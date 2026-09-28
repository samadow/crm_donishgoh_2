from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.models import Student
from academics.permissions import AdminWritePermission
from .models import (
    Announcement, Assignment, AssignmentSubmission, ConfirmedPayment, HRDocument, HROrder,
    IntegrationEndpoint, InternalMessage, LearningMaterial, LibraryItem, LibraryLoan, Notification,
    PaymentSchedule, QuizAttempt, ResearchMilestone, ResearchProject, RiskCase, RiskCaseNote,
    SelfCheckQuiz, StaffEmployee, StudentContract, StudentService, WorkLog,
)
from .permissions import AcademicContentPermission, AdminOnly
from .serializers import (
    AnnouncementSerializer, AssignmentSerializer, AssignmentSubmissionSerializer, ConfirmedPaymentSerializer,
    HRDocumentSerializer, HROrderSerializer, IntegrationEndpointSerializer, InternalMessageSerializer,
    LearningMaterialSerializer, LibraryItemSerializer, LibraryLoanSerializer, NotificationSerializer,
    PaymentScheduleSerializer, QuizAttemptSerializer, ResearchMilestoneSerializer, ResearchProjectSerializer,
    RiskCaseNoteSerializer, RiskCaseSerializer, SelfCheckQuizSerializer, StaffEmployeeSerializer,
    StudentContractSerializer, StudentServiceSerializer, WorkLogSerializer,
)


def scope_offerings(queryset, user, field="offering"):
    if user.role == "teacher":
        return queryset.filter(**{f"{field}__teacher__user": user})
    if user.role == "student":
        return queryset.filter(**{f"{field}__group__students__user": user})
    return queryset


class LearningMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = LearningMaterialSerializer
    permission_classes = [AcademicContentPermission]
    filterset_fields = ("offering", "kind", "language", "is_published")
    search_fields = ("title", "description", "offering__subject__name_ru")

    def get_queryset(self):
        queryset = LearningMaterial.objects.select_related("offering__teacher__user", "offering__group", "offering__subject", "published_by")
        queryset = scope_offerings(queryset, self.request.user)
        return queryset.filter(is_published=True) if self.request.user.role == "student" else queryset

    def perform_create(self, serializer):
        offering = serializer.validated_data["offering"]
        if self.request.user.role == "teacher" and offering.teacher.user_id != self.request.user.id:
            raise PermissionDenied("This course is assigned to another teacher.")
        serializer.save(published_by=self.request.user)


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = [AcademicContentPermission]
    filterset_fields = ("offering", "is_published")

    def get_queryset(self):
        queryset = Assignment.objects.select_related("offering__teacher__user", "offering__group", "offering__subject", "created_by")
        queryset = scope_offerings(queryset, self.request.user)
        return queryset.filter(is_published=True) if self.request.user.role == "student" else queryset

    def perform_create(self, serializer):
        offering = serializer.validated_data["offering"]
        if self.request.user.role == "teacher" and offering.teacher.user_id != self.request.user.id:
            raise PermissionDenied()
        serializer.save(created_by=self.request.user)


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSubmissionSerializer
    filterset_fields = ("assignment", "student", "status")

    def get_queryset(self):
        queryset = AssignmentSubmission.objects.select_related("assignment__offering__teacher__user", "student__user", "graded_by")
        user = self.request.user
        if user.role == "student":
            return queryset.filter(student__user=user)
        if user.role == "teacher":
            return queryset.filter(assignment__offering__teacher__user=user)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role != "student":
            raise PermissionDenied("Students create their own submissions.")
        student = Student.objects.get(user=self.request.user)
        assignment = serializer.validated_data["assignment"]
        if not assignment.is_published or assignment.offering.group_id != student.group_id:
            raise PermissionDenied("This assignment is not available to you.")
        status_value = serializer.validated_data.get("status", AssignmentSubmission.Status.DRAFT)
        if status_value not in {AssignmentSubmission.Status.DRAFT, AssignmentSubmission.Status.SUBMITTED}:
            raise ValidationError({"status": "A student can only save a draft or submit work."})
        serializer.save(student=student, submitted_at=timezone.now() if status_value == AssignmentSubmission.Status.SUBMITTED else None, score=None, feedback="", graded_by=None)

    def perform_update(self, serializer):
        submission = serializer.instance
        user = self.request.user
        if user.role == "student":
            if submission.student.user_id != user.id or submission.status == AssignmentSubmission.Status.GRADED:
                raise PermissionDenied()
            status_value = serializer.validated_data.get("status", submission.status)
            if status_value not in {AssignmentSubmission.Status.DRAFT, AssignmentSubmission.Status.SUBMITTED}:
                raise ValidationError({"status": "A student cannot grade a submission."})
            serializer.save(student=submission.student, score=submission.score, feedback=submission.feedback, graded_by=submission.graded_by, submitted_at=timezone.now() if status_value == AssignmentSubmission.Status.SUBMITTED else submission.submitted_at)
        elif user.role == "teacher" and submission.assignment.offering.teacher.user_id == user.id:
            serializer.save(student=submission.student, graded_by=user, status=AssignmentSubmission.Status.GRADED)
        elif user.role == "admin":
            serializer.save()
        else:
            raise PermissionDenied()

    def perform_destroy(self, instance):
        user = self.request.user
        if user.role == "admin":
            instance.delete()
            return
        if user.role == "student" and instance.student.user_id == user.id and instance.status == AssignmentSubmission.Status.DRAFT:
            instance.delete()
            return
        raise PermissionDenied("Only draft submissions can be removed by their owner.")


class SelfCheckQuizViewSet(viewsets.ModelViewSet):
    serializer_class = SelfCheckQuizSerializer
    permission_classes = [AcademicContentPermission]
    filterset_fields = ("offering", "is_published")

    def get_queryset(self):
        queryset = SelfCheckQuiz.objects.select_related("offering__teacher__user", "offering__group", "offering__subject", "created_by")
        queryset = scope_offerings(queryset, self.request.user)
        return queryset.filter(is_published=True) if self.request.user.role == "student" else queryset

    def perform_create(self, serializer):
        offering = serializer.validated_data["offering"]
        if self.request.user.role == "teacher" and offering.teacher.user_id != self.request.user.id:
            raise PermissionDenied()
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        if request.user.role != "student":
            raise PermissionDenied("Only students submit self-check attempts.")
        quiz = self.get_object()
        answers = request.data.get("answers")
        if not isinstance(answers, list) or len(answers) != len(quiz.questions):
            raise ValidationError({"answers": "Answer every question."})
        correct = sum(1 for index, question in enumerate(quiz.questions) if answers[index] == question.get("correct_index"))
        attempt = QuizAttempt.objects.create(quiz=quiz, student=Student.objects.get(user=request.user), answers=answers, correct_count=correct, total_count=len(quiz.questions))
        return Response(QuizAttemptSerializer(attempt).data)


class QuizAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuizAttemptSerializer

    def get_queryset(self):
        queryset = QuizAttempt.objects.select_related("quiz__offering__teacher__user", "student__user")
        if self.request.user.role == "student":
            return queryset.filter(student__user=self.request.user)
        if self.request.user.role == "teacher":
            return queryset.filter(quiz__offering__teacher__user=self.request.user)
        return queryset


class StudentContractViewSet(viewsets.ModelViewSet):
    serializer_class = StudentContractSerializer
    permission_classes = [AdminWritePermission]
    filterset_fields = ("student", "status", "currency")

    def get_queryset(self):
        queryset = StudentContract.objects.select_related("student__user").prefetch_related("schedule", "payments__confirmed_by")
        if self.request.user.role == "student":
            return queryset.filter(student__user=self.request.user)
        if self.request.user.role == "teacher":
            return queryset.none()
        return queryset


class PaymentScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentScheduleSerializer
    permission_classes = [AdminWritePermission]

    def get_queryset(self):
        queryset = PaymentSchedule.objects.select_related("contract__student__user")
        if self.request.user.role == "student":
            return queryset.filter(contract__student__user=self.request.user)
        if self.request.user.role == "teacher":
            return queryset.none()
        return queryset


class ConfirmedPaymentViewSet(viewsets.ModelViewSet):
    serializer_class = ConfirmedPaymentSerializer
    permission_classes = [AdminWritePermission]

    def get_queryset(self):
        queryset = ConfirmedPayment.objects.select_related("contract__student__user", "confirmed_by")
        if self.request.user.role == "student":
            return queryset.filter(contract__student__user=self.request.user)
        if self.request.user.role == "teacher":
            return queryset.none()
        return queryset

    def perform_create(self, serializer):
        serializer.save(confirmed_by=self.request.user)


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [AdminWritePermission]
    filterset_fields = ("audience", "is_pinned")

    def get_queryset(self):
        now = timezone.now()
        queryset = Announcement.objects.select_related("published_by").filter(publish_at__lte=now).filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))
        if self.request.user.role != "admin":
            queryset = queryset.filter(Q(audience=Announcement.Audience.ALL) | Q(audience=self.request.user.role))
        return queryset

    def perform_create(self, serializer):
        serializer.save(published_by=self.request.user)


class InternalMessageViewSet(viewsets.ModelViewSet):
    serializer_class = InternalMessageSerializer
    http_method_names = ("get", "post", "head", "options")
    search_fields = ("subject", "body", "sender__first_name", "recipient__first_name")

    def get_queryset(self):
        return InternalMessage.objects.select_related("sender", "recipient").filter(Q(sender=self.request.user) | Q(recipient=self.request.user))

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        message = self.get_object()
        if message.recipient_id != request.user.id:
            raise PermissionDenied()
        message.read_at = timezone.now()
        message.save(update_fields=("read_at",))
        return Response(self.get_serializer(message).data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.save(update_fields=("read_at",))
        return Response(self.get_serializer(notification).data)


class AdminOnlyModelViewSet(viewsets.ModelViewSet):
    permission_classes = [AdminOnly]


class StaffEmployeeViewSet(AdminOnlyModelViewSet):
    queryset = StaffEmployee.objects.select_related("user", "faculty")
    serializer_class = StaffEmployeeSerializer
    search_fields = ("employee_id", "full_name", "department", "position")
    filterset_fields = ("faculty", "status", "department")


class HRDocumentViewSet(AdminOnlyModelViewSet):
    queryset = HRDocument.objects.select_related("employee")
    serializer_class = HRDocumentSerializer
    filterset_fields = ("employee", "document_type")


class HROrderViewSet(AdminOnlyModelViewSet):
    queryset = HROrder.objects.select_related("employee", "created_by")
    serializer_class = HROrderSerializer
    filterset_fields = ("employee", "order_type")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class WorkLogViewSet(AdminOnlyModelViewSet):
    queryset = WorkLog.objects.select_related("employee", "approved_by")
    serializer_class = WorkLogSerializer
    filterset_fields = ("employee", "date")

    def perform_create(self, serializer):
        serializer.save(approved_by=self.request.user)


class ResearchProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ResearchProjectSerializer
    filterset_fields = ("student", "supervisor", "project_type", "status")

    def get_queryset(self):
        queryset = ResearchProject.objects.select_related("student__user", "supervisor__user").prefetch_related("milestones")
        if self.request.user.role == "student":
            return queryset.filter(student__user=self.request.user)
        if self.request.user.role == "teacher":
            return queryset.filter(supervisor__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role == "student":
            raise PermissionDenied()
        if self.request.user.role == "teacher" and serializer.validated_data["supervisor"].user_id != self.request.user.id:
            raise PermissionDenied()
        serializer.save()

    def perform_update(self, serializer):
        if self.request.user.role == "student" or (self.request.user.role == "teacher" and serializer.instance.supervisor.user_id != self.request.user.id):
            raise PermissionDenied()
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role == "admin" or (
            self.request.user.role == "teacher" and instance.supervisor.user_id == self.request.user.id
        ):
            instance.delete()
            return
        raise PermissionDenied()


class ResearchMilestoneViewSet(viewsets.ModelViewSet):
    serializer_class = ResearchMilestoneSerializer

    def get_queryset(self):
        queryset = ResearchMilestone.objects.select_related("project__student__user", "project__supervisor__user")
        if self.request.user.role == "student":
            return queryset.filter(project__student__user=self.request.user)
        if self.request.user.role == "teacher":
            return queryset.filter(project__supervisor__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        if self.request.user.role == "student" or (self.request.user.role == "teacher" and project.supervisor.user_id != self.request.user.id):
            raise PermissionDenied()
        serializer.save()

    def perform_update(self, serializer):
        project = serializer.instance.project
        if self.request.user.role == "student" or (
            self.request.user.role == "teacher" and project.supervisor.user_id != self.request.user.id
        ):
            raise PermissionDenied()
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role == "admin" or (
            self.request.user.role == "teacher" and instance.project.supervisor.user_id == self.request.user.id
        ):
            instance.delete()
            return
        raise PermissionDenied()


class RiskCaseViewSet(viewsets.ModelViewSet):
    serializer_class = RiskCaseSerializer
    filterset_fields = ("student", "severity", "status", "assigned_to")

    def get_queryset(self):
        queryset = RiskCase.objects.select_related("student__user", "assigned_to", "created_by").prefetch_related("notes__author")
        if self.request.user.role == "student":
            return queryset.none()
        if self.request.user.role == "teacher":
            return queryset.filter(student__group__offerings__teacher__user=self.request.user).distinct()
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role != "admin":
            raise PermissionDenied()
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if self.request.user.role != "admin":
            raise PermissionDenied()
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role != "admin":
            raise PermissionDenied()
        instance.delete()


class RiskCaseNoteViewSet(viewsets.ModelViewSet):
    serializer_class = RiskCaseNoteSerializer

    def get_queryset(self):
        queryset = RiskCaseNote.objects.select_related("case__student__group", "author")
        if self.request.user.role == "student":
            return queryset.none()
        if self.request.user.role == "teacher":
            return queryset.filter(case__student__group__offerings__teacher__user=self.request.user).distinct()
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role == "student":
            raise PermissionDenied()
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        if self.request.user.role != "admin" and serializer.instance.author_id != self.request.user.id:
            raise PermissionDenied()
        serializer.save(author=serializer.instance.author)

    def perform_destroy(self, instance):
        if self.request.user.role != "admin" and instance.author_id != self.request.user.id:
            raise PermissionDenied()
        instance.delete()


class LibraryItemViewSet(viewsets.ModelViewSet):
    queryset = LibraryItem.objects.all()
    serializer_class = LibraryItemSerializer
    permission_classes = [AdminWritePermission]
    search_fields = ("title", "authors", "isbn")


class LibraryLoanViewSet(viewsets.ModelViewSet):
    serializer_class = LibraryLoanSerializer
    permission_classes = [AdminWritePermission]

    def get_queryset(self):
        queryset = LibraryLoan.objects.select_related("item", "student__user")
        if self.request.user.role == "student":
            return queryset.filter(student__user=self.request.user)
        if self.request.user.role == "teacher":
            return queryset.none()
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        item = LibraryItem.objects.select_for_update().get(pk=serializer.validated_data["item"].pk)
        if serializer.validated_data.get("returned_at") is None:
            if item.available_copies < 1:
                raise ValidationError({"item": "No copy is currently available."})
            item.available_copies -= 1
            item.save(update_fields=("available_copies",))
        serializer.save(item=item)

    @transaction.atomic
    def perform_update(self, serializer):
        loan = serializer.instance
        item = LibraryItem.objects.select_for_update().get(pk=loan.item_id)
        old_active = loan.returned_at is None
        new_returned = serializer.validated_data.get("returned_at", loan.returned_at)
        new_active = new_returned is None
        if old_active and not new_active:
            item.available_copies = min(item.total_copies, item.available_copies + 1)
        elif not old_active and new_active:
            if item.available_copies < 1:
                raise ValidationError({"item": "No copy is currently available."})
            item.available_copies -= 1
        item.save(update_fields=("available_copies",))
        serializer.save(item=item)

    @transaction.atomic
    def perform_destroy(self, instance):
        item = LibraryItem.objects.select_for_update().get(pk=instance.item_id)
        if instance.returned_at is None:
            item.available_copies = min(item.total_copies, item.available_copies + 1)
            item.save(update_fields=("available_copies",))
        instance.delete()


class StudentServiceViewSet(viewsets.ModelViewSet):
    queryset = StudentService.objects.all()
    serializer_class = StudentServiceSerializer
    permission_classes = [AdminWritePermission]
    filterset_fields = ("is_active",)


class IntegrationEndpointViewSet(AdminOnlyModelViewSet):
    queryset = IntegrationEndpoint.objects.select_related("updated_by")
    serializer_class = IntegrationEndpointSerializer

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CampusOverviewView(APIView):
    def get(self, request):
        user = request.user
        if user.role == "student":
            student = Student.objects.get(user=user)
            contracts = StudentContract.objects.filter(student=student, status=StudentContract.Status.ACTIVE)
            return Response({
                "materials": LearningMaterial.objects.filter(offering__group=student.group, is_published=True).count(),
                "assignments": Assignment.objects.filter(offering__group=student.group, is_published=True).count(),
                "announcements": Announcement.objects.filter(Q(audience="all") | Q(audience="student"), publish_at__lte=timezone.now()).count(),
                "balance": str(sum((contract.balance for contract in contracts), 0)),
                "loans": LibraryLoan.objects.filter(student=student, returned_at__isnull=True).count(),
                "research": ResearchProject.objects.filter(student=student).count(),
            })
        if user.role == "teacher":
            return Response({
                "materials": LearningMaterial.objects.filter(offering__teacher__user=user).count(),
                "assignments": Assignment.objects.filter(offering__teacher__user=user).count(),
                "submissions": AssignmentSubmission.objects.filter(assignment__offering__teacher__user=user, status=AssignmentSubmission.Status.SUBMITTED).count(),
                "research": ResearchProject.objects.filter(supervisor__user=user).count(),
                "messages": InternalMessage.objects.filter(recipient=user, read_at__isnull=True).count(),
            })
        return Response({
            "staff": StaffEmployee.objects.filter(status=StaffEmployee.Status.ACTIVE).count(),
            "contracts": StudentContract.objects.filter(status=StudentContract.Status.ACTIVE).count(),
            "risk_cases": RiskCase.objects.exclude(status=RiskCase.Status.RESOLVED).count(),
            "announcements": Announcement.objects.count(),
            "library_items": LibraryItem.objects.count(),
            "integrations_waiting": IntegrationEndpoint.objects.filter(status=IntegrationEndpoint.Status.CONFIG_REQUIRED).count(),
        })
