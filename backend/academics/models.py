from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Faculty(TimeStampedModel):
    code = models.CharField(max_length=24, unique=True)
    name_tj = models.CharField(max_length=200)
    name_ru = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)

    class Meta:
        ordering = ("code",)
        verbose_name_plural = "faculties"

    def __str__(self):
        return self.name_ru


class Program(TimeStampedModel):
    class Degree(models.TextChoices):
        BACHELOR = "bachelor", "Bachelor"
        MASTER = "master", "Master"
        PHD = "phd", "PhD"

    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="programs")
    code = models.CharField(max_length=32, unique=True)
    name_tj = models.CharField(max_length=200)
    name_ru = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    degree = models.CharField(max_length=16, choices=Degree.choices, default=Degree.BACHELOR)
    duration_years = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(8)])

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} · {self.name_ru}"


class Teacher(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile")
    employee_id = models.CharField(max_length=32, unique=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="teachers")
    position = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ("user__last_name", "user__first_name")

    def __str__(self):
        return self.user.display_name


class Group(TimeStampedModel):
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="groups")
    code = models.CharField(max_length=32, unique=True)
    admission_year = models.PositiveSmallIntegerField()
    course = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(8)])
    curator = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name="curated_groups")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return self.code


class Room(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    building = models.CharField(max_length=120)
    capacity = models.PositiveSmallIntegerField(default=30)
    room_type = models.CharField(max_length=80, default="classroom")
    is_accessible = models.BooleanField(default=False)

    class Meta:
        ordering = ("building", "code")

    def __str__(self):
        return f"{self.building} · {self.code}"


class Subject(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name_tj = models.CharField(max_length=200)
    name_ru = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    credits = models.DecimalField(max_digits=4, decimal_places=1, default=3)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return self.name_ru


class Student(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ACADEMIC_LEAVE = "academic_leave", "Academic leave"
        EXPELLED = "expelled", "Expelled"
        GRADUATED = "graduated", "Graduated"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    student_id = models.CharField(max_length=32, unique=True)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="students")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    admission_date = models.DateField()
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ("user__last_name", "user__first_name")

    def __str__(self):
        return self.user.display_name


class StudentMovement(models.Model):
    class Kind(models.TextChoices):
        ENROLLMENT = "enrollment", "Enrollment"
        TRANSFER = "transfer", "Transfer"
        ACADEMIC_LEAVE = "academic_leave", "Academic leave"
        EXPULSION = "expulsion", "Expulsion"
        REINSTATEMENT = "reinstatement", "Reinstatement"
        GRADUATION = "graduation", "Graduation"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    effective_date = models.DateField()
    from_group = models.ForeignKey(Group, on_delete=models.PROTECT, null=True, blank=True, related_name="movements_from")
    to_group = models.ForeignKey(Group, on_delete=models.PROTECT, null=True, blank=True, related_name="movements_to")
    order_number = models.CharField(max_length=64, blank=True)
    reason = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student_movements_authored")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-effective_date", "-created_at")

