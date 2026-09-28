from django.conf import settings
from django.db import models

from academics.models import Faculty, Student, Teacher
from journal.models import CourseOffering


class LearningMaterial(models.Model):
    class Kind(models.TextChoices):
        SYLLABUS = "syllabus", "Syllabus"
        LECTURE = "lecture", "Lecture"
        PRESENTATION = "presentation", "Presentation"
        REFERENCE = "reference", "Reference"

    offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE, related_name="materials")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=2, choices=(("tj", "Тоҷикӣ"), ("ru", "Русский"), ("en", "English")), default="ru")
    file_name = models.CharField(max_length=255, blank=True)
    resource_url = models.URLField(blank=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="learning_materials_published")
    published_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ("-published_at",)


class Assignment(models.Model):
    offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=220)
    instructions = models.TextField()
    due_at = models.DateTimeField()
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assignments_created")
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("due_at",)


class AssignmentSubmission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        GRADED = "graded", "Graded"

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="assignment_submissions")
    text = models.TextField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="submissions_graded")
    submitted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("assignment", "student"), name="unique_assignment_student_submission")]


class SelfCheckQuiz(models.Model):
    offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE, related_name="self_check_quizzes")
    title = models.CharField(max_length=220)
    questions = models.JSONField(default=list, help_text="List of prompt, choices and correct_index objects")
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="quizzes_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(SelfCheckQuiz, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="quiz_attempts")
    answers = models.JSONField(default=list)
    correct_count = models.PositiveSmallIntegerField(default=0)
    total_count = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-completed_at",)


class StudentContract(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="contracts")
    number = models.CharField(max_length=64, unique=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="TJS")
    signed_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def paid_amount(self):
        return self.payments.filter(is_confirmed=True).aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def balance(self):
        return self.total_amount - self.paid_amount


class PaymentSchedule(models.Model):
    contract = models.ForeignKey(StudentContract, on_delete=models.CASCADE, related_name="schedule")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ("due_date",)


class ConfirmedPayment(models.Model):
    contract = models.ForeignKey(StudentContract, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    note = models.CharField(max_length=300, blank=True)
    is_confirmed = models.BooleanField(default=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments_confirmed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-payment_date",)


class Announcement(models.Model):
    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        ADMIN = "admin", "Administrators"
        TEACHER = "teacher", "Teachers"
        STUDENT = "student", "Students"

    audience = models.CharField(max_length=12, choices=Audience.choices, default=Audience.ALL)
    title_tj = models.CharField(max_length=220)
    title_ru = models.CharField(max_length=220)
    title_en = models.CharField(max_length=220)
    body_tj = models.TextField()
    body_ru = models.TextField()
    body_en = models.TextField()
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="announcements_published")
    publish_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ("-is_pinned", "-publish_at")


class InternalMessage(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="messages_sent")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_received")
    subject = models.CharField(max_length=220)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-sent_at",)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=32)
    title = models.CharField(max_length=220)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)


class StaffEmployee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        LEAVE = "leave", "On leave"
        TERMINATED = "terminated", "Terminated"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_profile")
    employee_id = models.CharField(max_length=32, unique=True)
    full_name = models.CharField(max_length=220)
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_members")
    department = models.CharField(max_length=180)
    position = models.CharField(max_length=180)
    hire_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)


class HRDocument(models.Model):
    employee = models.ForeignKey(StaffEmployee, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=64)
    title = models.CharField(max_length=220)
    number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class HROrder(models.Model):
    employee = models.ForeignKey(StaffEmployee, on_delete=models.PROTECT, related_name="orders")
    number = models.CharField(max_length=64, unique=True)
    order_type = models.CharField(max_length=64)
    order_date = models.DateField()
    summary = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="hr_orders_created")


class WorkLog(models.Model):
    employee = models.ForeignKey(StaffEmployee, on_delete=models.CASCADE, related_name="work_logs")
    date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    note = models.CharField(max_length=220, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="work_logs_approved")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("employee", "date"), name="unique_employee_work_date")]


class ResearchProject(models.Model):
    class Type(models.TextChoices):
        COURSEWORK = "coursework", "Coursework"
        THESIS = "thesis", "Thesis"

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        IN_PROGRESS = "in_progress", "In progress"
        READY = "ready", "Ready for defence"
        DEFENDED = "defended", "Defended"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="research_projects")
    supervisor = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name="research_projects")
    project_type = models.CharField(max_length=12, choices=Type.choices)
    title = models.CharField(max_length=300)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROPOSED)
    defence_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ResearchMilestone(models.Model):
    project = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=220)
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ("due_date",)


class RiskCase(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MONITORING = "monitoring", "Monitoring"
        RESOLVED = "resolved", "Resolved"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="risk_cases")
    category = models.CharField(max_length=64)
    severity = models.CharField(max_length=12, choices=(("low", "Low"), ("medium", "Medium"), ("high", "High")))
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="risk_cases_assigned")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="risk_cases_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class RiskCaseNote(models.Model):
    case = models.ForeignKey(RiskCase, on_delete=models.CASCADE, related_name="notes")
    text = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="risk_case_notes")
    created_at = models.DateTimeField(auto_now_add=True)


class LibraryItem(models.Model):
    title = models.CharField(max_length=300)
    authors = models.CharField(max_length=300)
    isbn = models.CharField(max_length=32, blank=True, db_index=True)
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)
    total_copies = models.PositiveSmallIntegerField(default=1)
    available_copies = models.PositiveSmallIntegerField(default=1)
    resource_url = models.URLField(blank=True)

    class Meta:
        ordering = ("title",)


class LibraryLoan(models.Model):
    item = models.ForeignKey(LibraryItem, on_delete=models.PROTECT, related_name="loans")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="library_loans")
    borrowed_at = models.DateField()
    due_at = models.DateField()
    returned_at = models.DateField(null=True, blank=True)


class StudentService(models.Model):
    code = models.CharField(max_length=32, unique=True)
    title_tj = models.CharField(max_length=220)
    title_ru = models.CharField(max_length=220)
    title_en = models.CharField(max_length=220)
    description_tj = models.TextField()
    description_ru = models.TextField()
    description_en = models.TextField()
    contact = models.CharField(max_length=220)
    is_active = models.BooleanField(default=True)


class IntegrationEndpoint(models.Model):
    class Kind(models.TextChoices):
        FACE_ID = "face_id", "Face ID"
        CAMERA = "camera", "Camera"
        SMS = "sms", "SMS"
        BANK = "bank", "Bank payments"
        PLAGIARISM = "plagiarism", "Plagiarism check"
        CONFERENCE = "conference", "Online conferences"

    class Status(models.TextChoices):
        DISABLED = "disabled", "Disabled"
        CONFIG_REQUIRED = "config_required", "Configuration required"
        ACTIVE = "active", "Active"

    kind = models.CharField(max_length=24, choices=Kind.choices, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIG_REQUIRED)
    provider_name = models.CharField(max_length=120, blank=True)
    public_note = models.CharField(max_length=300, default="External provider credentials and infrastructure are required.")
    configuration_schema = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ("kind",)
