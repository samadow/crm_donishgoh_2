from rest_framework import serializers

from .models import (
    Announcement, Assignment, AssignmentSubmission, ConfirmedPayment, HRDocument, HROrder,
    IntegrationEndpoint, InternalMessage, LearningMaterial, LibraryItem, LibraryLoan, Notification,
    PaymentSchedule, QuizAttempt, ResearchMilestone, ResearchProject, RiskCase, RiskCaseNote,
    SelfCheckQuiz, StaffEmployee, StudentContract, StudentService, WorkLog,
)


class LearningMaterialSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="offering.subject.name_ru", read_only=True)
    group_code = serializers.CharField(source="offering.group.code", read_only=True)
    published_by_name = serializers.CharField(source="published_by.display_name", read_only=True)

    class Meta:
        model = LearningMaterial
        fields = "__all__"
        read_only_fields = ("published_by", "published_at")


class AssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="offering.subject.name_ru", read_only=True)
    group_code = serializers.CharField(source="offering.group.code", read_only=True)

    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ("created_by", "created_at")


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.display_name", read_only=True)
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = "__all__"
        read_only_fields = ("student", "graded_by", "submitted_at", "updated_at")


class SelfCheckQuizSerializer(serializers.ModelSerializer):
    public_questions = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    questions = serializers.JSONField(write_only=True, required=False)
    subject_name = serializers.CharField(source="offering.subject.name_ru", read_only=True)

    def get_public_questions(self, obj):
        return [{"prompt": item.get("prompt", ""), "choices": item.get("choices", [])} for item in obj.questions]

    def get_question_count(self, obj):
        return len(obj.questions)

    class Meta:
        model = SelfCheckQuiz
        fields = ("id", "offering", "subject_name", "title", "questions", "public_questions", "question_count", "is_published", "created_by", "created_at")
        read_only_fields = ("created_by", "created_at")

    def validate_questions(self, value):
        for index, question in enumerate(value):
            choices = question.get("choices", [])
            correct = question.get("correct_index")
            if not question.get("prompt") or len(choices) < 2 or not isinstance(correct, int) or correct < 0 or correct >= len(choices):
                raise serializers.ValidationError(f"Question {index + 1} is incomplete.")
        return value


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ("id", "quiz", "quiz_title", "correct_count", "total_count", "completed_at")


class PaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSchedule
        fields = "__all__"


class ConfirmedPaymentSerializer(serializers.ModelSerializer):
    confirmed_by_name = serializers.CharField(source="confirmed_by.display_name", read_only=True)

    class Meta:
        model = ConfirmedPayment
        fields = "__all__"
        read_only_fields = ("confirmed_by", "created_at")


class StudentContractSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.display_name", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    schedule = PaymentScheduleSerializer(many=True, read_only=True)
    payments = ConfirmedPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = StudentContract
        fields = "__all__"
        read_only_fields = ("created_at",)


class AnnouncementSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    published_by_name = serializers.CharField(source="published_by.display_name", read_only=True)

    def language(self):
        request = self.context.get("request")
        return request.query_params.get("lang", "ru") if request else "ru"

    def get_title(self, obj):
        return getattr(obj, f"title_{self.language()}", obj.title_ru)

    def get_body(self, obj):
        return getattr(obj, f"body_{self.language()}", obj.body_ru)

    class Meta:
        model = Announcement
        fields = "__all__"
        read_only_fields = ("published_by",)


class InternalMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.display_name", read_only=True)
    recipient_name = serializers.CharField(source="recipient.display_name", read_only=True)

    class Meta:
        model = InternalMessage
        fields = "__all__"
        read_only_fields = ("sender", "sent_at", "read_at")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("user", "created_at", "read_at")


class StaffEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffEmployee
        fields = "__all__"


class HRDocumentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = HRDocument
        fields = "__all__"
        read_only_fields = ("created_at",)


class HROrderSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = HROrder
        fields = "__all__"
        read_only_fields = ("created_by",)


class WorkLogSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = WorkLog
        fields = "__all__"
        read_only_fields = ("approved_by",)


class ResearchMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchMilestone
        fields = "__all__"


class ResearchProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.display_name", read_only=True)
    supervisor_name = serializers.CharField(source="supervisor.user.display_name", read_only=True)
    milestones = ResearchMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchProject
        fields = "__all__"
        read_only_fields = ("created_at",)


class RiskCaseNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True)

    class Meta:
        model = RiskCaseNote
        fields = "__all__"
        read_only_fields = ("author", "created_at")


class RiskCaseSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.display_name", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.display_name", read_only=True)
    notes = RiskCaseNoteSerializer(many=True, read_only=True)

    class Meta:
        model = RiskCase
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")


class LibraryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryItem
        fields = "__all__"


class LibraryLoanSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source="item.title", read_only=True)
    student_name = serializers.CharField(source="student.user.display_name", read_only=True)

    class Meta:
        model = LibraryLoan
        fields = "__all__"

    def validate(self, attrs):
        borrowed = attrs.get("borrowed_at", getattr(self.instance, "borrowed_at", None))
        due = attrs.get("due_at", getattr(self.instance, "due_at", None))
        returned = attrs.get("returned_at", getattr(self.instance, "returned_at", None))
        if borrowed and due and due < borrowed:
            raise serializers.ValidationError({"due_at": "Due date must not precede the borrowed date."})
        if borrowed and returned and returned < borrowed:
            raise serializers.ValidationError({"returned_at": "Return date must not precede the borrowed date."})
        return attrs


class StudentServiceSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def language(self):
        request = self.context.get("request")
        return request.query_params.get("lang", "ru") if request else "ru"

    def get_title(self, obj):
        return getattr(obj, f"title_{self.language()}", obj.title_ru)

    def get_description(self, obj):
        return getattr(obj, f"description_{self.language()}", obj.description_ru)

    class Meta:
        model = StudentService
        fields = "__all__"


class IntegrationEndpointSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = IntegrationEndpoint
        fields = "__all__"
        read_only_fields = ("updated_at", "updated_by")
