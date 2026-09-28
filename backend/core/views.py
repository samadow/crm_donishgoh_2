from django.db.models import Avg, Count, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.models import Group, Student, Teacher
from journal.models import AttendanceRecord, ClassSession, CourseOffering, UniversityPolicy
from journal.serializers import ClassSessionSerializer


class DashboardView(APIView):
    def get(self, request):
        role = request.user.role
        if role == "admin":
            return Response(self.admin_dashboard(request))
        if role == "teacher":
            return Response(self.teacher_dashboard(request))
        return Response(self.student_dashboard(request))

    def today_sessions(self, request, queryset):
        today = timezone.localdate()
        items = queryset.filter(date=today).select_related(
            "offering__group", "offering__subject", "offering__teacher__user", "offering__semester__academic_year", "room"
        ).annotate(record_count=Count("records")).order_by("start_time")
        return ClassSessionSerializer(items, many=True, context={"request": request}).data

    def admin_dashboard(self, request):
        today = timezone.localdate()
        sessions = ClassSession.objects.all()
        unmarked = sessions.filter(date__lte=today, records__isnull=True).distinct().count()
        active_students = Student.objects.filter(status=Student.Status.ACTIVE).count()
        alerts = []
        if unmarked:
            alerts.append({"kind": "warning", "key": "unmarked_sessions", "count": unmarked})
        return {
            "role": "admin",
            "stats": {
                "students": active_students,
                "teachers": Teacher.objects.count(),
                "groups": Group.objects.filter(is_active=True).count(),
                "today_sessions": sessions.filter(date=today).count(),
            },
            "today": self.today_sessions(request, sessions),
            "alerts": alerts,
        }

    def teacher_dashboard(self, request):
        sessions = ClassSession.objects.filter(offering__teacher__user=request.user)
        offerings = CourseOffering.objects.filter(teacher__user=request.user, is_active=True)
        return {
            "role": "teacher",
            "stats": {
                "courses": offerings.count(),
                "groups": offerings.values("group").distinct().count(),
                "today_sessions": sessions.filter(date=timezone.localdate()).count(),
                "open_entries": AttendanceRecord.objects.filter(session__offering__teacher__user=request.user, is_confirmed=False).count(),
            },
            "today": self.today_sessions(request, sessions),
            "alerts": [],
        }

    def student_dashboard(self, request):
        student = Student.objects.select_related("group").get(user=request.user)
        sessions = ClassSession.objects.filter(offering__group=student.group)
        records = AttendanceRecord.objects.filter(student=student)
        missed_hours = records.filter(status=AttendanceRecord.Status.ABSENT).aggregate(
            total=Sum("session__academic_hours")
        )["total"] or 0
        graded = records.exclude(grade__isnull=True)
        grade_average = graded.aggregate(value=Avg("grade"))["value"]
        policy = UniversityPolicy.objects.first()
        thresholds = policy.attendance_warning_thresholds if policy else [35, 36, 47, 48]
        alerts = []
        reached = [value for value in thresholds if missed_hours >= value]
        if reached:
            alerts.append({"kind": "warning", "key": "attendance_threshold", "hours": missed_hours, "threshold": max(reached)})
        return {
            "role": "student",
            "stats": {
                "subjects": CourseOffering.objects.filter(group=student.group, is_active=True).count(),
                "today_sessions": sessions.filter(date=timezone.localdate()).count(),
                "missed_hours": missed_hours,
                "grade_average": round(float(grade_average), 2) if grade_average is not None else None,
            },
            "today": self.today_sessions(request, sessions),
            "alerts": alerts,
        }

