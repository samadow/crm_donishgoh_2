from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from academics.models import Student
from journal.exceptions import ConflictError
from .models import AssessmentSaveOperation, ExamResult, ExamResultChange, ExamSheet


def result_snapshot(result):
    return {
        "score": str(result.score) if result.score is not None else None,
        "grade_label": result.grade_label,
        "comment": result.comment,
        "status": result.status,
        "version": result.version,
    }


def normalize_score(value, maximum):
    if value in (None, ""):
        return None
    try:
        score = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError({"score": "Score must be numeric."}) from exc
    if score < 0 or score > maximum:
        raise ValidationError({"score": f"Score must be between 0 and {maximum}."})
    return score


@transaction.atomic
def save_exam_results(*, sheet, entries, user, idempotency_key):
    previous = AssessmentSaveOperation.objects.filter(user=user, key=idempotency_key).first()
    if previous:
        return previous.response_data, True
    if user.role == "teacher" and sheet.offering.teacher.user_id != user.id:
        raise PermissionDenied("This assessment belongs to another teacher.")
    if user.role not in {"admin", "teacher"}:
        raise PermissionDenied("Assessment editing is not available for this role.")
    students = {student.id: student for student in Student.objects.filter(group=sheet.offering.group, status=Student.Status.ACTIVE)}
    response = []
    for entry in entries:
        student = students.get(int(entry.get("student_id", 0)))
        if not student:
            raise ValidationError({"student_id": "The student does not belong to this group."})
        result = ExamResult.objects.select_for_update().filter(sheet=sheet, student=student).first()
        score = normalize_score(entry.get("score"), sheet.max_score)
        values = {"score": score, "grade_label": str(entry.get("grade_label", "")), "comment": str(entry.get("comment", ""))}
        if result is None:
            if sheet.status == ExamSheet.Status.APPROVED:
                raise ValidationError({"sheet": "Approved sheets cannot receive new results."})
            result = ExamResult.objects.create(sheet=sheet, student=student, updated_by=user, **values)
            response.append({"student_id": student.id, "pending": False, **result_snapshot(result)})
            continue
        if int(entry.get("version", 0)) != result.version:
            raise ConflictError({"detail": "The exam result was changed by another user.", "student_id": student.id, "current": result_snapshot(result)})
        changed = any(getattr(result, field) != value for field, value in values.items())
        if not changed:
            response.append({"student_id": student.id, "pending": False, **result_snapshot(result)})
            continue
        if result.status == ExamResult.Status.APPROVED or sheet.status == ExamSheet.Status.APPROVED:
            reason = str(entry.get("reason", "")).strip()
            if not reason:
                raise ValidationError({"reason": "A reason is required to change an approved result."})
            ExamResultChange.objects.create(
                result=result,
                old_value=result_snapshot(result),
                new_value={**result_snapshot(result), **{key: str(value) if isinstance(value, Decimal) else value for key, value in values.items()}},
                reason=reason,
                author=user,
            )
            response.append({"student_id": student.id, "pending": True, **result_snapshot(result)})
            continue
        for field, value in values.items():
            setattr(result, field, value)
        result.version += 1
        result.updated_by = user
        result.save(update_fields=(*values.keys(), "version", "updated_by", "updated_at"))
        response.append({"student_id": student.id, "pending": False, **result_snapshot(result)})
    payload = {"results": response}
    AssessmentSaveOperation.objects.create(user=user, key=idempotency_key, response_data=payload)
    return payload, False


@transaction.atomic
def review_result_change(*, change, reviewer, approve):
    change = ExamResultChange.objects.select_for_update().get(pk=change.pk)
    if change.status != ExamResultChange.Status.PENDING:
        raise ConflictError("This grade correction has already been reviewed.")
    result = ExamResult.objects.select_for_update().get(pk=change.result_id)
    if result_snapshot(result) != change.old_value:
        raise ConflictError({"detail": "The result changed after the correction was submitted.", "current": result_snapshot(result)})
    change.reviewer = reviewer
    change.reviewed_at = timezone.now()
    if approve:
        result.score = change.new_value.get("score")
        result.grade_label = change.new_value.get("grade_label", "")
        result.comment = change.new_value.get("comment", "")
        result.version += 1
        result.updated_by = reviewer
        result.save(update_fields=("score", "grade_label", "comment", "version", "updated_by", "updated_at"))
        change.status = ExamResultChange.Status.APPROVED
    else:
        change.status = ExamResultChange.Status.REJECTED
    change.save(update_fields=("reviewer", "reviewed_at", "status"))
    return change

