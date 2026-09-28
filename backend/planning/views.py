from datetime import date

from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from academics.permissions import AdminWritePermission
from journal.models import ClassSession
from .models import CurriculumPlan, CurriculumSubject, ScheduleEntry, TeacherWorkload
from .serializers import CurriculumPlanSerializer, CurriculumSubjectSerializer, ScheduleEntrySerializer, TeacherWorkloadSerializer
from .services import save_schedule_entry


class CurriculumPlanViewSet(viewsets.ModelViewSet):
    queryset = CurriculumPlan.objects.select_related("program", "academic_year", "created_by").prefetch_related("subjects__subject")
    serializer_class = CurriculumPlanSerializer
    permission_classes = [AdminWritePermission]
    filterset_fields = ("program", "academic_year", "status")
    search_fields = ("name", "program__code", "program__name_ru")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CurriculumSubjectViewSet(viewsets.ModelViewSet):
    queryset = CurriculumSubject.objects.select_related("plan", "subject")
    serializer_class = CurriculumSubjectSerializer
    permission_classes = [AdminWritePermission]
    filterset_fields = ("plan", "course", "semester_number", "assessment_type")


class TeacherWorkloadViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherWorkloadSerializer
    permission_classes = [AdminWritePermission]
    filterset_fields = ("teacher", "group", "semester")

    def get_queryset(self):
        queryset = TeacherWorkload.objects.select_related("teacher__user", "group", "semester", "curriculum_subject__subject")
        if self.request.user.role == "teacher":
            return queryset.filter(teacher__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class ScheduleEntryViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleEntrySerializer
    permission_classes = [AdminWritePermission]
    filterset_fields = ("offering", "weekday", "room", "is_active")
    ordering_fields = ("weekday", "start_time", "effective_from")

    def get_queryset(self):
        queryset = ScheduleEntry.objects.select_related("offering__group", "offering__subject", "offering__teacher__user", "room", "created_by")
        user = self.request.user
        if user.role == "teacher":
            return queryset.filter(offering__teacher__user=user)
        if user.role == "student":
            return queryset.filter(offering__group__students__user=user)
        return queryset

    def perform_create(self, serializer):
        serializer.instance = save_schedule_entry(created_by=self.request.user, **serializer.validated_data)

    def perform_update(self, serializer):
        values = {
            "offering": serializer.validated_data.get("offering", serializer.instance.offering),
            "weekday": serializer.validated_data.get("weekday", serializer.instance.weekday),
            "start_time": serializer.validated_data.get("start_time", serializer.instance.start_time),
            "end_time": serializer.validated_data.get("end_time", serializer.instance.end_time),
            "room": serializer.validated_data.get("room", serializer.instance.room),
            "effective_from": serializer.validated_data.get("effective_from", serializer.instance.effective_from),
            "effective_to": serializer.validated_data.get("effective_to", serializer.instance.effective_to),
            "is_active": serializer.validated_data.get("is_active", serializer.instance.is_active),
            "created_by": serializer.instance.created_by,
        }
        serializer.instance = save_schedule_entry(instance=serializer.instance, **values)

    @action(detail=True, methods=["post"], url_path="create-session")
    def create_session(self, request, pk=None):
        entry = self.get_object()
        if request.user.role != "admin":
            raise PermissionDenied("Only an administrator can create timetable sessions.")
        try:
            session_date = date.fromisoformat(str(request.data.get("date", "")))
        except ValueError as exc:
            raise ValidationError({"date": "Use ISO date format YYYY-MM-DD."}) from exc
        topic = str(request.data.get("topic", "")).strip()
        if not topic:
            raise ValidationError({"topic": "A session topic is required."})
        if session_date.weekday() != entry.weekday or not entry.effective_from <= session_date <= entry.effective_to:
            raise ValidationError({"date": "The date does not match this schedule entry."})
        try:
            session = ClassSession.objects.create(
                offering=entry.offering,
                date=session_date,
                start_time=entry.start_time,
                end_time=entry.end_time,
                topic=topic,
                session_type=request.data.get("session_type", ClassSession.SessionType.LECTURE),
                room=entry.room,
                academic_hours=request.data.get("academic_hours", 2),
            )
        except IntegrityError as exc:
            raise ValidationError({"date": "This class session already exists."}) from exc
        from journal.serializers import ClassSessionSerializer
        return Response(ClassSessionSerializer(session, context={"request": request}).data)
