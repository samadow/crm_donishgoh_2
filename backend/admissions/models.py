from django.conf import settings
from django.db import models
from django.db.models import Q

from academics.models import Group, Program, Student
from journal.models import AcademicYear


class Applicant(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, blank=True)
    birth_date = models.DateField()
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=32)
    national_id = models.CharField(max_length=64, blank=True)
    address = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("national_id",), condition=~Q(national_id=""), name="unique_nonempty_applicant_national_id")
        ]

    @property
    def display_name(self):
        return " ".join(part for part in (self.last_name, self.first_name, self.middle_name) if part)

    def __str__(self):
        return self.display_name


class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        DOCUMENTS_VERIFIED = "documents_verified", "Documents verified"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        ENROLLED = "enrolled", "Enrolled"

    applicant = models.ForeignKey(Applicant, on_delete=models.PROTECT, related_name="applications")
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="applications")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="applications")
    application_number = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True)
    source = models.CharField(max_length=64, default="office")
    submitted_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="admission_applications_assigned")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.application_number} · {self.applicant.display_name}"


class ApplicantDocument(models.Model):
    class Type(models.TextChoices):
        PASSPORT = "passport", "Passport"
        CERTIFICATE = "certificate", "Education certificate"
        PHOTO = "photo", "Photo"
        MEDICAL = "medical", "Medical certificate"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        MISSING = "missing", "Missing"
        RECEIVED = "received", "Received"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=24, choices=Type.choices)
    title = models.CharField(max_length=180)
    identifier = models.CharField(max_length=100, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.MISSING)
    notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="admission_documents_verified")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("document_type", "created_at")
        constraints = [models.UniqueConstraint(fields=("application", "document_type"), name="unique_application_document_type")]


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    reason = models.TextField(blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="admission_status_changes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Application status history is immutable.")
        return super().save(*args, **kwargs)


class EnrollmentResult(models.Model):
    application = models.OneToOneField(Application, on_delete=models.PROTECT, related_name="enrollment")
    student = models.OneToOneField(Student, on_delete=models.PROTECT, related_name="admission_enrollment")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="admission_enrollments")
    order_number = models.CharField(max_length=64)
    enrolled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="admission_enrollments_created")
    enrolled_at = models.DateTimeField(auto_now_add=True)


class AdmissionImportBatch(models.Model):
    class Status(models.TextChoices):
        PREVIEW = "preview", "Preview"
        COMMITTED = "committed", "Committed"

    file_name = models.CharField(max_length=255)
    rows = models.JSONField(default=list)
    row_count = models.PositiveIntegerField(default=0)
    valid_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PREVIEW)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="admission_imports")
    created_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
