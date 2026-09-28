from rest_framework import serializers

from .models import CurriculumPlan, CurriculumSubject, ScheduleEntry, TeacherWorkload


class CurriculumSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name_ru", read_only=True)
    subject_name_tj = serializers.CharField(source="subject.name_tj", read_only=True)
    subject_name_en = serializers.CharField(source="subject.name_en", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    total_hours = serializers.IntegerField(read_only=True)

    class Meta:
        model = CurriculumSubject
        fields = "__all__"


class CurriculumPlanSerializer(serializers.ModelSerializer):
    program_code = serializers.CharField(source="program.code", read_only=True)
    program_name = serializers.CharField(source="program.name_ru", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    subjects = CurriculumSubjectSerializer(many=True, read_only=True)

    class Meta:
        model = CurriculumPlan
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")


class TeacherWorkloadSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.user.display_name", read_only=True)
    group_code = serializers.CharField(source="group.code", read_only=True)
    subject_name = serializers.CharField(source="curriculum_subject.subject.name_ru", read_only=True)

    class Meta:
        model = TeacherWorkload
        fields = "__all__"
        read_only_fields = ("assigned_by", "created_at")


class ScheduleEntrySerializer(serializers.ModelSerializer):
    group_code = serializers.CharField(source="offering.group.code", read_only=True)
    subject_name = serializers.CharField(source="offering.subject.name_ru", read_only=True)
    subject_name_tj = serializers.CharField(source="offering.subject.name_tj", read_only=True)
    subject_name_en = serializers.CharField(source="offering.subject.name_en", read_only=True)
    teacher_name = serializers.CharField(source="offering.teacher.user.display_name", read_only=True)
    room_label = serializers.CharField(source="room.__str__", read_only=True)
    weekday_label = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = ScheduleEntry
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        date_from = attrs.get("effective_from", getattr(self.instance, "effective_from", None))
        date_to = attrs.get("effective_to", getattr(self.instance, "effective_to", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        if date_from and date_to and date_to < date_from:
            raise serializers.ValidationError({"effective_to": "End date must not precede start date."})
        return attrs

