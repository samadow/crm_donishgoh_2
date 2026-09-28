from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from academics.models import Student
from .exceptions import ConflictError
from .models import AttendanceRecord, JournalChange, SaveOperation, Semester


EDITABLE_FIELDS = ("status", "grade", "grade_type", "comment", "is_confirmed")


def record_snapshot(record):
    return {
        "status": record.status,
        "grade": str(record.grade) if record.grade is not None else None,
        "grade_type": record.grade_type,
        "comment": record.comment,
        "is_confirmed": record.is_confirmed,
        "version": record.version,
    }


def normalize_entry(entry):
    normalized = {field: entry[field] for field in EDITABLE_FIELDS if field in entry}
    if "grade" in normalized and normalized["grade"] not in (None, ""):
        try:
            normalized["grade"] = Decimal(str(normalized["grade"]))
        except Exception as exc:
            raise ValidationError({"grade": "Grade must be numeric."}) from exc
    elif normalized.get("grade") == "":
        normalized["grade"] = None
    return normalized


@transaction.atomic
def save_session_records(*, session, entries, user, idempotency_key):
    previous = SaveOperation.objects.filter(user=user, key=idempotency_key).first()
    if previous:
        return previous.response_data, True

    if user.role == "teacher" and session.offering.teacher.user_id != user.id:
        raise PermissionDenied("This class is assigned to another teacher.")
    if user.role not in {"admin", "teacher"}:
        raise PermissionDenied("Journal editing is not available for this role.")

    group_students = {
        item.id: item
        for item in Student.objects.filter(group=session.offering.group, status=Student.Status.ACTIVE).select_related("user")
    }
    result = []
    pending_count = 0

    for entry in entries:
        try:
            student_id = int(entry["student_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError({"entries": "Every entry must include a valid student_id."}) from exc
        student = group_students.get(student_id)
        if student is None:
            raise ValidationError({"student_id": f"Student {student_id} does not belong to this group."})

        record = AttendanceRecord.objects.select_for_update().filter(session=session, student=student).first()
        values = normalize_entry(entry)
        reason = str(entry.get("reason", "")).strip()

        if record is None:
            record = AttendanceRecord.objects.create(session=session, student=student, updated_by=user, **values)
            result.append({"id": record.id, "student_id": student.id, **record_snapshot(record), "pending": False})
            continue

        expected_version = entry.get("version")
        if expected_version is None or int(expected_version) != record.version:
            raise ConflictError({
                "detail": "The journal entry changed after you opened it.",
                "student_id": student.id,
                "current": record_snapshot(record),
            })

        old_value = record_snapshot(record)
        changed = any(getattr(record, field) != value for field, value in values.items())
        if not changed:
            result.append({"id": record.id, "student_id": student.id, **old_value, "pending": False})
            continue

        if record.is_confirmed and not reason:
            raise ValidationError({"reason": f"A reason is required to change the confirmed entry for student {student.id}."})

        next_value = {**old_value}
        next_value.update({key: str(value) if isinstance(value, Decimal) else value for key, value in values.items()})

        if record.is_confirmed and session.offering.semester.status == Semester.Status.CLOSED:
            JournalChange.objects.create(
                record=record,
                old_value=old_value,
                new_value=next_value,
                reason=reason,
                author=user,
                status=JournalChange.Status.PENDING,
            )
            pending_count += 1
            result.append({"id": record.id, "student_id": student.id, **old_value, "pending": True})
            continue

        for field, value in values.items():
            setattr(record, field, value)
        record.version += 1
        record.updated_by = user
        record.save(update_fields=(*values.keys(), "version", "updated_by", "updated_at"))
        if old_value["is_confirmed"] or values.get("is_confirmed"):
            JournalChange.objects.create(
                record=record,
                old_value=old_value,
                new_value=record_snapshot(record),
                reason=reason or "Initial confirmation",
                author=user,
                status=JournalChange.Status.APPLIED,
            )
        result.append({"id": record.id, "student_id": student.id, **record_snapshot(record), "pending": False})

    response = {"records": result, "pending_approval": pending_count, "saved": len(result) - pending_count}
    SaveOperation.objects.create(user=user, key=idempotency_key, response_data=response)
    return response, False


@transaction.atomic
def review_pending_change(*, change, reviewer, approve):
    change = JournalChange.objects.select_for_update().select_related("record").get(pk=change.pk)
    if change.status != JournalChange.Status.PENDING:
        raise ConflictError("This correction has already been reviewed.")
    record = AttendanceRecord.objects.select_for_update().get(pk=change.record_id)
    if record_snapshot(record) != change.old_value:
        raise ConflictError({"detail": "The journal entry changed after this request was submitted.", "current": record_snapshot(record)})

    change.reviewer = reviewer
    change.reviewed_at = timezone.now()
    if approve:
        for field in EDITABLE_FIELDS:
            if field in change.new_value:
                setattr(record, field, change.new_value[field])
        record.version += 1
        record.updated_by = reviewer
        record.save(update_fields=(*EDITABLE_FIELDS, "version", "updated_by", "updated_at"))
        change.status = JournalChange.Status.APPROVED
    else:
        change.status = JournalChange.Status.REJECTED
    change.save(update_fields=("reviewer", "reviewed_at", "status"))
    return change
