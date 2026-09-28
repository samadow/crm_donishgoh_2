from rest_framework import serializers

from .models import AdmissionImportBatch, Applicant, ApplicantDocument, Application, ApplicationStatusHistory, EnrollmentResult


class AdmissionImportBatchSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)

    class Meta:
        model = AdmissionImportBatch
        fields = "__all__"
        read_only_fields = ("file_name", "rows", "row_count", "valid_count", "error_count", "status", "created_by", "created_at", "committed_at")


class ApplicantSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Applicant
        fields = ("id", "first_name", "last_name", "middle_name", "display_name", "birth_date", "email", "phone", "national_id", "address", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    def validate_email(self, value):
        queryset = Applicant.objects.filter(email__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("An applicant with this email already exists.")
        return value.lower()


class ApplicantDocumentSerializer(serializers.ModelSerializer):
    verified_by_name = serializers.CharField(source="verified_by.display_name", read_only=True)

    class Meta:
        model = ApplicantDocument
        fields = "__all__"
        read_only_fields = ("verified_by", "verified_at", "created_at")


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = ("id", "from_status", "to_status", "reason", "author_name", "created_at")


class EnrollmentResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.display_name", read_only=True)
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    group_code = serializers.CharField(source="group.code", read_only=True)

    class Meta:
        model = EnrollmentResult
        fields = ("id", "student", "student_name", "student_id", "group", "group_code", "order_number", "enrolled_at")


class ApplicationSerializer(serializers.ModelSerializer):
    applicant_detail = ApplicantSerializer(source="applicant", read_only=True)
    program_name = serializers.CharField(source="program.name_ru", read_only=True)
    program_name_tj = serializers.CharField(source="program.name_tj", read_only=True)
    program_name_en = serializers.CharField(source="program.name_en", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    documents = ApplicantDocumentSerializer(many=True, read_only=True)
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    enrollment = EnrollmentResultSerializer(read_only=True)

    class Meta:
        model = Application
        fields = ("id", "applicant", "applicant_detail", "program", "program_name", "program_name_tj", "program_name_en", "academic_year", "academic_year_name", "application_number", "status", "source", "submitted_at", "decision_at", "decision_reason", "assigned_to", "version", "documents", "status_history", "enrollment", "created_at", "updated_at")
        read_only_fields = ("status", "submitted_at", "decision_at", "decision_reason", "version", "created_at", "updated_at")
