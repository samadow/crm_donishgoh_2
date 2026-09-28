from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.models import Student
from journal.permissions import JournalPermission
from .models import ExamResult, ExamResultChange, ExamSheet
from .serializers import ExamResultChangeSerializer, ExamResultSerializer, ExamSheetSerializer
from .services import review_result_change, save_exam_results


class ExamSheetViewSet(viewsets.ModelViewSet):
    serializer_class = ExamSheetSerializer
    permission_classes = [JournalPermission]
    filterset_fields = ("offering", "assessment_type", "status", "exam_date")

    def get_queryset(self):
        queryset = ExamSheet.objects.select_related("offering__group", "offering__subject", "offering__teacher__user", "room", "created_by", "approved_by").prefetch_related("results__student__user", "results__updated_by")
        user = self.request.user
        if user.role == "teacher":
            return queryset.filter(offering__teacher__user=user)
        if user.role == "student":
            return queryset.filter(offering__group__students__user=user)
        return queryset

    def perform_create(self, serializer):
        offering = serializer.validated_data["offering"]
        if self.request.user.role == "teacher" and offering.teacher.user_id != self.request.user.id:
            raise PermissionDenied("This course is assigned to another teacher.")
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="save-results")
    def save_results(self, request, pk=None):
        sheet = self.get_object()
        entries = request.data.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValidationError({"entries": "Provide at least one result."})
        key = request.headers.get("Idempotency-Key") or request.data.get("request_id")
        if not key:
            raise ValidationError({"request_id": "An idempotency key is required."})
        data, repeated = save_exam_results(sheet=sheet, entries=entries, user=request.user, idempotency_key=str(key))
        return Response({**data, "idempotent_replay": repeated})

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        sheet = self.get_object()
        if request.user.role == "teacher" and sheet.offering.teacher.user_id != request.user.id:
            raise PermissionDenied()
        if sheet.status != ExamSheet.Status.DRAFT:
            raise ValidationError({"status": "Only a draft sheet can be submitted."})
        sheet.status = ExamSheet.Status.SUBMITTED
        sheet.version += 1
        sheet.save(update_fields=("status", "version", "updated_at"))
        return Response(self.get_serializer(sheet).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if request.user.role != "admin":
            raise PermissionDenied("Only an administrator can approve an exam sheet.")
        sheet = self.get_object()
        if sheet.status != ExamSheet.Status.SUBMITTED:
            raise ValidationError({"status": "Only a submitted sheet can be approved."})
        sheet.status = ExamSheet.Status.APPROVED
        sheet.approved_by = request.user
        sheet.approved_at = timezone.now()
        sheet.version += 1
        sheet.save(update_fields=("status", "approved_by", "approved_at", "version", "updated_at"))
        sheet.results.update(status=ExamResult.Status.APPROVED)
        return Response(self.get_serializer(sheet).data)


class ExamResultViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExamResultSerializer
    filterset_fields = ("sheet", "student", "status")

    def get_queryset(self):
        queryset = ExamResult.objects.select_related("sheet__offering__teacher__user", "student__user", "updated_by")
        user = self.request.user
        if user.role == "teacher":
            return queryset.filter(sheet__offering__teacher__user=user)
        if user.role == "student":
            return queryset.filter(student__user=user)
        return queryset


class ExamResultChangeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExamResultChangeSerializer

    def get_queryset(self):
        queryset = ExamResultChange.objects.select_related("result__student__user", "result__sheet__offering__teacher__user", "author", "reviewer")
        if self.request.user.role == "teacher":
            return queryset.filter(result__sheet__offering__teacher__user=self.request.user)
        if self.request.user.role == "student":
            return queryset.filter(result__student__user=self.request.user)
        return queryset

    def _review(self, request, approve):
        if request.user.role != "admin":
            raise PermissionDenied("Only an administrator can review grade corrections.")
        return Response(self.get_serializer(review_result_change(change=self.get_object(), reviewer=request.user, approve=approve)).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._review(request, True)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._review(request, False)


class TranscriptView(APIView):
    def get(self, request):
        student_id = request.query_params.get("student")
        if request.user.role == "student":
            student = Student.objects.select_related("user", "group").get(user=request.user)
        elif student_id:
            student = Student.objects.select_related("user", "group").get(pk=student_id)
            if request.user.role == "teacher" and not student.group.offerings.filter(teacher__user=request.user).exists():
                raise PermissionDenied("This student is not in one of your groups.")
        else:
            raise ValidationError({"student": "Select a student."})
        results = ExamResult.objects.filter(student=student, status=ExamResult.Status.APPROVED).select_related("sheet__offering__subject", "sheet__offering__semester__academic_year")
        records = [{
            "subject_code": result.sheet.offering.subject.code,
            "subject_name": result.sheet.offering.subject.name_ru,
            "subject_name_tj": result.sheet.offering.subject.name_tj,
            "subject_name_en": result.sheet.offering.subject.name_en,
            "credits": str(result.sheet.offering.subject.credits),
            "assessment_type": result.sheet.assessment_type,
            "score": str(result.score) if result.score is not None else None,
            "grade_label": result.grade_label,
            "academic_year": result.sheet.offering.semester.academic_year.name,
            "semester": result.sheet.offering.semester.number,
        } for result in results]
        return Response({
            "student": {"id": student.id, "student_id": student.student_id, "name": student.user.display_name, "group": student.group.code},
            "records": records,
            "note": "GPA is not calculated until the university configures an official grading scale.",
        })

