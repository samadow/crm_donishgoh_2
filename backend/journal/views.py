import uuid
from datetime import date, timedelta

from django.db.models import Avg, Case, Count, F, IntegerField, Q, Sum, Value, When
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from academics.permissions import AdminWritePermission
from .models import AcademicYear, AttendanceRecord, ClassSession, CourseOffering, JournalChange, Semester, UniversityPolicy
from .permissions import AdminWritePolicyPermission, JournalPermission
from .serializers import AcademicYearSerializer, AttendanceRecordSerializer, ClassSessionSerializer, CourseOfferingSerializer, JournalChangeSerializer, SemesterSerializer, UniversityPolicySerializer
from .services import review_pending_change, save_session_records


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [AdminWritePermission]


class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.select_related("academic_year")
    serializer_class = SemesterSerializer
    permission_classes = [AdminWritePermission]
    filterset_fields = ("academic_year", "status")


class CourseOfferingViewSet(viewsets.ModelViewSet):
    serializer_class = CourseOfferingSerializer
    permission_classes = [JournalPermission]
    filterset_fields = ("group", "subject", "teacher", "semester", "is_active")
    search_fields = ("group__code", "subject__name_tj", "subject__name_ru", "subject__name_en", "teacher__user__last_name")

    def get_queryset(self):
        queryset = CourseOffering.objects.select_related("group", "subject", "teacher__user", "semester__academic_year").annotate(student_count=Count("group__students", filter=Q(group__students__status="active")))
        user = self.request.user
        if user.role == "teacher":
            return queryset.filter(teacher__user=user)
        if user.role == "student":
            return queryset.filter(group__students__user=user, is_active=True)
        return queryset


class ClassSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ClassSessionSerializer
    permission_classes = [JournalPermission]
    filterset_fields = ("offering", "date", "session_type")
    search_fields = ("topic", "offering__group__code", "offering__subject__name_ru")
    ordering_fields = ("date", "start_time", "academic_hours")

    def get_queryset(self):
        queryset = ClassSession.objects.select_related(
            "offering__group", "offering__subject", "offering__teacher__user", "offering__semester__academic_year", "room"
        ).annotate(record_count=Count("records"))
        user = self.request.user
        if user.role == "teacher":
            return queryset.filter(offering__teacher__user=user)
        if user.role == "student":
            return queryset.filter(offering__group__students__user=user)
        return queryset

    def perform_create(self, serializer):
        offering = serializer.validated_data["offering"]
        if self.request.user.role == "teacher" and offering.teacher.user_id != self.request.user.id:
            raise PermissionDenied("This class is assigned to another teacher.")
        serializer.save()

    @action(detail=True, methods=["get"])
    def records(self, request, pk=None):
        session = self.get_object()
        queryset = AttendanceRecord.objects.filter(session=session).select_related("student__user", "student__group", "updated_by")
        if request.user.role == "student":
            queryset = queryset.filter(student__user=request.user)
        return Response(AttendanceRecordSerializer(queryset, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="bulk-mark")
    def bulk_mark(self, request, pk=None):
        session = self.get_object()
        entries = request.data.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValidationError({"entries": "Provide at least one journal entry."})
        idempotency_key = request.headers.get("Idempotency-Key") or request.data.get("request_id")
        if not idempotency_key:
            raise ValidationError({"request_id": "An idempotency key is required."})
        if len(str(idempotency_key)) > 128:
            raise ValidationError({"request_id": "The idempotency key is too long."})
        response_data, repeated = save_session_records(
            session=session,
            entries=entries,
            user=request.user,
            idempotency_key=str(idempotency_key),
        )
        return Response({**response_data, "idempotent_replay": repeated})


class AttendanceRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [JournalPermission]
    filterset_fields = ("session", "student", "status", "grade_type", "is_confirmed")
    search_fields = ("student__user__first_name", "student__user__last_name", "student__student_id")

    def get_queryset(self):
        queryset = AttendanceRecord.objects.select_related("session__offering__teacher__user", "session__offering__group", "student__user", "student__group", "updated_by")
        user = self.request.user
        if user.role == "teacher":
            return queryset.filter(session__offering__teacher__user=user)
        if user.role == "student":
            return queryset.filter(student__user=user)
        return queryset

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        record = self.get_object()
        return Response(JournalChangeSerializer(record.changes.select_related("author", "reviewer"), many=True).data)

    @action(detail=False, methods=["get"])
    def report(self, request):
        period = request.query_params.get("period", "month")
        if period not in {"day", "week", "month", "semester"}:
            raise ValidationError({"period": "Choose day, week, month or semester."})
        try:
            anchor = date.fromisoformat(request.query_params.get("date", str(date.today())))
        except ValueError as exc:
            raise ValidationError({"date": "Use YYYY-MM-DD."}) from exc
        queryset = self.get_queryset()
        if offering := request.query_params.get("offering"):
            queryset = queryset.filter(session__offering_id=offering)
        if group := request.query_params.get("group"):
            queryset = queryset.filter(session__offering__group_id=group)
        if subject := request.query_params.get("subject"):
            queryset = queryset.filter(session__offering__subject_id=subject)
        if student := request.query_params.get("student"):
            queryset = queryset.filter(student_id=student)

        if period == "day":
            start = end = anchor
        elif period == "week":
            start = anchor - timedelta(days=anchor.weekday())
            end = start + timedelta(days=6)
        elif period == "month":
            start = anchor.replace(day=1)
            end = (start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)) - timedelta(days=1)
        else:
            semester_id = request.query_params.get("semester")
            if not semester_id and offering:
                semester_id = CourseOffering.objects.filter(pk=offering).values_list("semester_id", flat=True).first()
            try:
                semester = Semester.objects.get(pk=semester_id)
            except (Semester.DoesNotExist, ValueError, TypeError) as exc:
                raise ValidationError({"semester": "Select a semester or course offering."}) from exc
            start, end = semester.start_date, semester.end_date
            queryset = queryset.filter(session__offering__semester=semester)

        queryset = queryset.filter(session__date__range=(start, end))
        hour_sum = lambda attendance_status: Sum(
            Case(
                When(status=attendance_status, then=F("session__academic_hours")),
                default=Value(0), output_field=IntegerField(),
            )
        )
        rows = list(queryset.values(
            "student_id", "student__student_id", "student__user__first_name", "student__user__last_name",
        ).annotate(
            entries=Count("id"),
            present_hours=hour_sum(AttendanceRecord.Status.PRESENT),
            absent_hours=hour_sum(AttendanceRecord.Status.ABSENT),
            late_hours=hour_sum(AttendanceRecord.Status.LATE),
            excused_hours=hour_sum(AttendanceRecord.Status.EXCUSED),
            average_grade=Avg("grade"),
        ).order_by("student__user__last_name", "student__user__first_name"))
        for row in rows:
            row["average_grade"] = str(round(row["average_grade"], 2)) if row["average_grade"] is not None else None
        overall = queryset.aggregate(
            entries=Count("id"),
            present_hours=hour_sum(AttendanceRecord.Status.PRESENT),
            absent_hours=hour_sum(AttendanceRecord.Status.ABSENT),
            late_hours=hour_sum(AttendanceRecord.Status.LATE),
            excused_hours=hour_sum(AttendanceRecord.Status.EXCUSED),
            average_grade=Avg("grade"),
        )
        overall = {key: (0 if value is None and key != "average_grade" else str(round(value, 2)) if key == "average_grade" and value is not None else value) for key, value in overall.items()}
        return Response({"period": period, "start": start, "end": end, "overall": overall, "students": rows})


class JournalChangeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JournalChangeSerializer
    filterset_fields = ("status", "author", "record")

    def get_queryset(self):
        queryset = JournalChange.objects.select_related("record__session__offering__teacher__user", "record__session__offering__subject", "record__session__offering__group", "record__student__user", "author", "reviewer")
        user = self.request.user
        if user.role == "teacher":
            return queryset.filter(record__session__offering__teacher__user=user)
        if user.role == "student":
            return queryset.filter(record__student__user=user)
        return queryset

    def _review(self, request, approve):
        if request.user.role != "admin":
            raise PermissionDenied("Only an administrator can review a closed-semester correction.")
        change = self.get_object()
        reviewed = review_pending_change(change=change, reviewer=request.user, approve=approve)
        return Response(self.get_serializer(reviewed).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._review(request, True)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._review(request, False)


class UniversityPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = UniversityPolicySerializer
    permission_classes = [AdminWritePolicyPermission]

    def get_queryset(self):
        return UniversityPolicy.objects.select_related("updated_by")

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
