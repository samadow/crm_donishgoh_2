from django.conf import settings
from django.db import models

from academics.models import Room, Student
from journal.models import CourseOffering


class ExamSheet(models.Model):
    class Type(models.TextChoices):
        CONTROL = "control", "Control"
        EXAM = "exam", "Exam"
        FINAL = "final", "Final"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"

    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="exam_sheets")
    assessment_type = models.CharField(max_length=16, choices=Type.choices, default=Type.EXAM)
    exam_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, null=True, blank=True, related_name="exam_sheets")
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    passing_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exam_sheets_created")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="exam_sheets_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-exam_date", "offering__group__code")
        constraints = [models.UniqueConstraint(fields=("offering", "assessment_type", "exam_date"), name="unique_offering_assessment_date")]


class ExamResult(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"

    sheet = models.ForeignKey(ExamSheet, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="exam_results")
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    grade_label = models.CharField(max_length=16, blank=True)
    comment = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exam_results_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("student__user__last_name", "student__user__first_name")
        constraints = [models.UniqueConstraint(fields=("sheet", "student"), name="unique_exam_result_student")]


class ExamResultChange(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    result = models.ForeignKey(ExamResult, on_delete=models.CASCADE, related_name="changes")
    old_value = models.JSONField()
    new_value = models.JSONField()
    reason = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exam_changes_authored")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="exam_changes_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class AssessmentSaveOperation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=128)
    response_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "key"), name="unique_assessment_save_operation")]

