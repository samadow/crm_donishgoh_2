from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from academics.models import Group, Program, Room, Subject, Teacher
from journal.models import AcademicYear, CourseOffering, Semester


class CurriculumPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="curriculum_plans")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="curriculum_plans")
    name = models.CharField(max_length=180)
    version = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="curriculum_plans_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-academic_year__start_date", "program__code", "-version")
        constraints = [models.UniqueConstraint(fields=("program", "academic_year", "version"), name="unique_curriculum_version")]


class CurriculumSubject(models.Model):
    class AssessmentType(models.TextChoices):
        CREDIT = "credit", "Credit"
        EXAM = "exam", "Exam"
        DIFFERENTIATED_CREDIT = "differentiated_credit", "Differentiated credit"

    plan = models.ForeignKey(CurriculumPlan, on_delete=models.CASCADE, related_name="subjects")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="curriculum_entries")
    course = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(8)])
    semester_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(16)])
    lecture_hours = models.PositiveSmallIntegerField(default=0)
    practice_hours = models.PositiveSmallIntegerField(default=0)
    lab_hours = models.PositiveSmallIntegerField(default=0)
    independent_hours = models.PositiveSmallIntegerField(default=0)
    credits = models.DecimalField(max_digits=4, decimal_places=1)
    assessment_type = models.CharField(max_length=24, choices=AssessmentType.choices)

    class Meta:
        ordering = ("course", "semester_number", "subject__code")
        constraints = [models.UniqueConstraint(fields=("plan", "subject", "semester_number"), name="unique_subject_in_curriculum_semester")]

    @property
    def total_hours(self):
        return self.lecture_hours + self.practice_hours + self.lab_hours + self.independent_hours


class TeacherWorkload(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name="workloads")
    curriculum_subject = models.ForeignKey(CurriculumSubject, on_delete=models.PROTECT, related_name="workloads")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="workloads")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="workloads")
    planned_hours = models.PositiveSmallIntegerField()
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="workloads_assigned")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("teacher", "curriculum_subject", "group", "semester"), name="unique_teacher_workload")]


class ScheduleEntry(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE, related_name="schedule_entries")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="schedule_entries")
    effective_from = models.DateField()
    effective_to = models.DateField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="schedule_entries_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("weekday", "start_time", "offering__group__code")
        constraints = [
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="schedule_end_after_start"),
            models.CheckConstraint(condition=models.Q(effective_to__gte=models.F("effective_from")), name="schedule_valid_date_range"),
            models.UniqueConstraint(fields=("offering", "weekday", "start_time", "effective_from"), name="unique_offering_schedule_start"),
        ]

