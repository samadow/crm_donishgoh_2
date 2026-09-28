from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from academics.models import Student, StudentMovement
from .models import Application, ApplicationStatusHistory, EnrollmentResult

User = get_user_model()

ALLOWED_TRANSITIONS = {
    Application.Status.DRAFT: {Application.Status.SUBMITTED},
    Application.Status.SUBMITTED: {Application.Status.UNDER_REVIEW, Application.Status.REJECTED},
    Application.Status.UNDER_REVIEW: {Application.Status.DOCUMENTS_VERIFIED, Application.Status.REJECTED},
    Application.Status.DOCUMENTS_VERIFIED: {Application.Status.ACCEPTED, Application.Status.REJECTED},
    Application.Status.ACCEPTED: {Application.Status.ENROLLED},
    Application.Status.REJECTED: {Application.Status.UNDER_REVIEW},
    Application.Status.ENROLLED: set(),
}


@transaction.atomic
def transition_application(*, application, target_status, author, reason=""):
    application = Application.objects.select_for_update().get(pk=application.pk)
    if target_status == application.status:
        return application
    if target_status not in ALLOWED_TRANSITIONS.get(application.status, set()):
        raise ValidationError({"status": f"Transition from {application.status} to {target_status} is not allowed."})
    previous = application.status
    application.status = target_status
    application.version += 1
    now = timezone.now()
    fields = ["status", "version", "updated_at"]
    if target_status == Application.Status.SUBMITTED:
        application.submitted_at = now
        fields.append("submitted_at")
    if target_status in {Application.Status.ACCEPTED, Application.Status.REJECTED}:
        application.decision_at = now
        application.decision_reason = reason
        fields.extend(("decision_at", "decision_reason"))
    application.save(update_fields=fields)
    ApplicationStatusHistory.objects.create(
        application=application,
        from_status=previous,
        to_status=target_status,
        reason=reason,
        author=author,
    )
    return application


@transaction.atomic
def enroll_application(*, application, group, author, order_number, temporary_password):
    application = Application.objects.select_for_update().select_related("applicant", "program").get(pk=application.pk)
    existing = EnrollmentResult.objects.select_related("student__user", "group").filter(application=application).first()
    if existing:
        return existing, True
    if application.status != Application.Status.ACCEPTED:
        raise ValidationError({"status": "Only an accepted application can be enrolled."})
    if group.program_id != application.program_id:
        raise ValidationError({"group": "The group belongs to a different academic programme."})
    if not temporary_password or len(temporary_password) < 12:
        raise ValidationError({"temporary_password": "Provide a temporary password with at least 12 characters."})
    applicant = application.applicant
    user = User.objects.filter(email__iexact=applicant.email).first()
    if user and (user.role != User.Role.STUDENT or hasattr(user, "student_profile")):
        raise ValidationError({"email": "This email already belongs to another university account."})
    if user is None:
        user = User.objects.create_user(
            email=applicant.email,
            password=temporary_password,
            first_name=applicant.first_name,
            last_name=applicant.last_name,
            role=User.Role.STUDENT,
        )
    else:
        user.set_password(temporary_password)
        user.first_name = applicant.first_name
        user.last_name = applicant.last_name
        user.save(update_fields=("password", "first_name", "last_name"))
    student_id = f"S-{application.academic_year.start_date.year}-{application.pk:05d}"
    student = Student.objects.create(
        user=user,
        student_id=student_id,
        group=group,
        status=Student.Status.ACTIVE,
        admission_date=timezone.localdate(),
        phone=applicant.phone,
    )
    StudentMovement.objects.create(
        student=student,
        kind=StudentMovement.Kind.ENROLLMENT,
        effective_date=student.admission_date,
        to_group=group,
        order_number=order_number,
        reason=f"Enrolled from application {application.application_number}",
        author=author,
    )
    result = EnrollmentResult.objects.create(
        application=application,
        student=student,
        group=group,
        order_number=order_number,
        enrolled_by=author,
    )
    transition_application(application=application, target_status=Application.Status.ENROLLED, author=author, reason=order_number)
    return result, False

