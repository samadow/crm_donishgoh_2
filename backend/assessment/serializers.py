from rest_framework import serializers

from .models import ExamResult, ExamResultChange, ExamSheet


class ExamResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.display_name", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    updated_by_name = serializers.CharField(source="updated_by.display_name", read_only=True)

    class Meta:
        model = ExamResult
        fields = "__all__"
        read_only_fields = ("version", "updated_by", "created_at", "updated_at")


class ExamSheetSerializer(serializers.ModelSerializer):
    group_code = serializers.CharField(source="offering.group.code", read_only=True)
    subject_name = serializers.CharField(source="offering.subject.name_ru", read_only=True)
    subject_name_tj = serializers.CharField(source="offering.subject.name_tj", read_only=True)
    subject_name_en = serializers.CharField(source="offering.subject.name_en", read_only=True)
    teacher_name = serializers.CharField(source="offering.teacher.user.display_name", read_only=True)
    room_label = serializers.CharField(source="room.__str__", read_only=True)
    results = ExamResultSerializer(many=True, read_only=True)

    class Meta:
        model = ExamSheet
        fields = "__all__"
        read_only_fields = ("status", "version", "created_by", "approved_by", "approved_at", "created_at", "updated_at")


class ExamResultChangeSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True)
    reviewer_name = serializers.CharField(source="reviewer.display_name", read_only=True)
    student_name = serializers.CharField(source="result.student.user.display_name", read_only=True)

    class Meta:
        model = ExamResultChange
        fields = "__all__"

