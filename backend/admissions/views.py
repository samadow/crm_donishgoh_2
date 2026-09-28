from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser

from academics.models import Group
from academics.permissions import AdminOnlyPermission
from .imports import build_import_preview, commit_import_batch
from .models import AdmissionImportBatch, Applicant, ApplicantDocument, Application
from .serializers import AdmissionImportBatchSerializer, ApplicantDocumentSerializer, ApplicantSerializer, ApplicationSerializer, EnrollmentResultSerializer
from .services import enroll_application, transition_application


class AdminModelViewSet(viewsets.ModelViewSet):
    permission_classes = [AdminOnlyPermission]


class ApplicantViewSet(AdminModelViewSet):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantSerializer
    search_fields = ("first_name", "last_name", "middle_name", "email", "phone", "national_id")
    ordering_fields = ("created_at", "last_name")


class ApplicationViewSet(AdminModelViewSet):
    serializer_class = ApplicationSerializer
    filterset_fields = ("status", "program", "academic_year", "assigned_to")
    search_fields = ("application_number", "applicant__first_name", "applicant__last_name", "applicant__email")
    ordering_fields = ("created_at", "updated_at", "application_number")

    def get_queryset(self):
        return Application.objects.select_related("applicant", "program", "academic_year", "assigned_to", "enrollment__student__user", "enrollment__group").prefetch_related("documents__verified_by", "status_history__author")

    def perform_create(self, serializer):
        application = serializer.save()
        from .models import ApplicationStatusHistory
        ApplicationStatusHistory.objects.create(application=application, from_status="", to_status=application.status, reason="Application created", author=self.request.user)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def intake(self, request):
        applicant_serializer = ApplicantSerializer(data=request.data.get("applicant", {}), context={"request": request})
        applicant_serializer.is_valid(raise_exception=True)
        applicant = applicant_serializer.save()
        application_serializer = self.get_serializer(data={
            "applicant": applicant.id,
            "program": request.data.get("program"),
            "academic_year": request.data.get("academic_year"),
            "application_number": request.data.get("application_number"),
            "source": request.data.get("source", "office"),
        })
        application_serializer.is_valid(raise_exception=True)
        application = application_serializer.save()
        from .models import ApplicationStatusHistory
        ApplicationStatusHistory.objects.create(application=application, from_status="", to_status=application.status, reason="Application created", author=request.user)
        return Response(self.get_serializer(application).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        application = self.get_object()
        target = request.data.get("status")
        if target not in Application.Status.values:
            raise ValidationError({"status": "Unknown application status."})
        updated = transition_application(application=application, target_status=target, author=request.user, reason=str(request.data.get("reason", "")))
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        application = self.get_object()
        order_number = str(request.data.get("order_number", "")).strip()
        if not order_number:
            raise ValidationError({"order_number": "Order number is required."})
        try:
            group = Group.objects.get(pk=request.data.get("group"), is_active=True)
        except Group.DoesNotExist as exc:
            raise ValidationError({"group": "Select an active group."}) from exc
        result, repeated = enroll_application(
            application=application,
            group=group,
            author=request.user,
            order_number=order_number,
            temporary_password=str(request.data.get("temporary_password", "")),
        )
        return Response({"enrollment": EnrollmentResultSerializer(result).data, "idempotent_replay": repeated}, status=status.HTTP_200_OK)


class ApplicantDocumentViewSet(AdminModelViewSet):
    queryset = ApplicantDocument.objects.select_related("application", "verified_by")
    serializer_class = ApplicantDocumentSerializer
    filterset_fields = ("application", "document_type", "status")

    def perform_update(self, serializer):
        if serializer.validated_data.get("status") == ApplicantDocument.Status.VERIFIED:
            serializer.save(verified_by=self.request.user, verified_at=timezone.now())
        else:
            serializer.save()


class AdmissionImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdmissionImportBatch.objects.select_related("created_by")
    serializer_class = AdmissionImportBatchSerializer
    permission_classes = [AdminOnlyPermission]

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def preview(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            raise ValidationError({"file": "Select an .xlsx or .csv file."})
        batch = build_import_preview(uploaded_file, request.user)
        return Response(self.get_serializer(batch).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def commit(self, request, pk=None):
        batch, repeated = commit_import_batch(self.get_object(), request.user)
        return Response({"batch": self.get_serializer(batch).data, "idempotent_replay": repeated})
