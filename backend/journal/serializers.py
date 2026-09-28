from rest_framework import serializers

from academics.serializers import StudentSerializer
from .models import AcademicYear, AttendanceRecord, ClassSession, CourseOffering, JournalChange, Semester, UniversityPolicy


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = "__all__"


class SemesterSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = Semester
        fields = ("id", "academic_year", "academic_year_name", "number", "start_date", "end_date", "status")


class CourseOfferingSerializer(serializers.ModelSerializer):
    group_code = serializers.CharField(source="group.code", read_only=True)
    subject_name = serializers.CharField(source="subject.name_ru", read_only=True)
    subject_name_tj = serializers.CharField(source="subject.name_tj", read_only=True)
    subject_name_en = serializers.CharField(source="subject.name_en", read_only=True)
    teacher_name = serializers.CharField(source="teacher.user.display_name", read_only=True)
    semester_label = serializers.SerializerMethodField()
    student_count = serializers.IntegerField(read_only=True)

    def get_semester_label(self, obj):
        return f"{obj.semester.academic_year.name} · {obj.semester.number}"

    class Meta:
        model = CourseOffering
        fields = ("id", "group", "group_code", "subject", "subject_name", "subject_name_tj", "subject_name_en", "teacher", "teacher_name", "semester", "semester_label", "planned_hours", "is_active", "student_count")


class ClassSessionSerializer(serializers.ModelSerializer):
    offering_detail = CourseOfferingSerializer(source="offering", read_only=True)
    room_label = serializers.SerializerMethodField()
    record_count = serializers.IntegerField(read_only=True)

    def get_room_label(self, obj):
        return str(obj.room) if obj.room else ""

    class Meta:
        model = ClassSession
        fields = ("id", "offering", "offering_detail", "date", "start_time", "end_time", "topic", "session_type", "room", "room_label", "academic_hours", "version", "record_count")
        read_only_fields = ("version",)


class JournalChangeSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True)
    reviewer_name = serializers.CharField(source="reviewer.display_name", read_only=True)
    student_name = serializers.CharField(source="record.student.user.display_name", read_only=True)
    student_code = serializers.CharField(source="record.student.student_id", read_only=True)
    subject_name = serializers.CharField(source="record.session.offering.subject.name_ru", read_only=True)
    group_code = serializers.CharField(source="record.session.offering.group.code", read_only=True)
    session_date = serializers.DateField(source="record.session.date", read_only=True)

    class Meta:
        model = JournalChange
        fields = ("id", "record", "student_name", "student_code", "subject_name", "group_code", "session_date", "old_value", "new_value", "reason", "author_name", "status", "reviewer_name", "reviewed_at", "created_at")


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_detail = StudentSerializer(source="student", read_only=True)
    updated_by_name = serializers.CharField(source="updated_by.display_name", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ("id", "session", "student", "student_detail", "status", "grade", "grade_type", "comment", "is_confirmed", "version", "updated_by_name", "updated_at")
        read_only_fields = ("version", "updated_by_name", "updated_at")


class UniversityPolicySerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source="updated_by.display_name", read_only=True)

    class Meta:
        model = UniversityPolicy
        fields = ("id", "name", "attendance_warning_thresholds", "final_grade_rules", "updated_at", "updated_by_name")
        read_only_fields = ("updated_at", "updated_by_name")

    def validate_attendance_warning_thresholds(self, value):
        if not isinstance(value, list) or any(not isinstance(item, int) or item < 0 for item in value):
            raise serializers.ValidationError("Thresholds must be a list of non-negative whole hours.")
        return sorted(set(value))
