from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from academics.models import Group, Room, Student, Subject, Teacher


class AcademicYear(models.Model):
    name = models.CharField(max_length=24, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-start_date",)

    def __str__(self):
        return self.name


class Semester(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="semesters")
    number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(3)])
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True)

    class Meta:
        ordering = ("-academic_year__start_date", "number")
        constraints = [models.UniqueConstraint(fields=("academic_year", "number"), name="unique_semester_in_year")]

    def __str__(self):
        return f"{self.academic_year.name} · {self.number}"


class UniversityPolicy(models.Model):
    name = models.CharField(max_length=120, default="University policy")
    attendance_warning_thresholds = models.JSONField(default=list)
    final_grade_rules = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.attendance_warning_thresholds:
            self.attendance_warning_thresholds = [35, 36, 47, 48]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CourseOffering(models.Model):
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="offerings")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="offerings")
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name="offerings")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="offerings")
    planned_hours = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("group__code", "subject__name_ru")
        constraints = [
            models.UniqueConstraint(fields=("group", "subject", "teacher", "semester"), name="unique_course_offering")
        ]

    def __str__(self):
        return f"{self.group.code} · {self.subject.name_ru}"


class ClassSession(models.Model):
    class SessionType(models.TextChoices):
        LECTURE = "lecture", "Lecture"
        PRACTICE = "practice", "Practice"
        LAB = "lab", "Laboratory"
        SEMINAR = "seminar", "Seminar"
        CONTROL = "control", "Control"
        EXAM = "exam", "Exam"

    offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    topic = models.CharField(max_length=300)
    session_type = models.CharField(max_length=16, choices=SessionType.choices, default=SessionType.LECTURE)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, null=True, blank=True, related_name="sessions")
    academic_hours = models.PositiveSmallIntegerField(default=2, validators=[MinValueValidator(1), MaxValueValidator(8)])
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date", "start_time")
        constraints = [
            models.UniqueConstraint(fields=("offering", "date", "start_time"), name="unique_offering_session_start")
        ]

    def __str__(self):
        return f"{self.offering} · {self.date} {self.start_time}"


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        UNMARKED = "unmarked", "Unmarked"
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    class GradeType(models.TextChoices):
        DAILY = "daily", "Daily"
        CONTROL = "control", "Control"
        INDEPENDENT = "independent", "Independent work"
        EXAM = "exam", "Exam"

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="records")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="attendance_records")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNMARKED)
    grade = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    grade_type = models.CharField(max_length=16, choices=GradeType.choices, default=GradeType.DAILY)
    comment = models.CharField(max_length=500, blank=True)
    is_confirmed = models.BooleanField(default=False, db_index=True)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="journal_records_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("student__user__last_name", "student__user__first_name")
        constraints = [models.UniqueConstraint(fields=("session", "student"), name="unique_student_session_record")]


class JournalChange(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    record = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name="changes")
    old_value = models.JSONField(default=dict)
    new_value = models.JSONField(default=dict)
    reason = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="journal_changes_authored")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.APPLIED)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="journal_changes_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class SaveOperation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=128)
    response_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "key"), name="unique_save_operation_per_user")]

