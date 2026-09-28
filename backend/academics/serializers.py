from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Faculty, Group, Program, Room, Student, StudentMovement, Subject, Teacher

User = get_user_model()


class LocalizedModelSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        language = self.context.get("request").query_params.get("lang", "ru") if self.context.get("request") else "ru"
        return getattr(obj, f"name_{language}", obj.name_ru)


class FacultySerializer(LocalizedModelSerializer):
    class Meta:
        model = Faculty
        fields = ("id", "code", "name", "name_tj", "name_ru", "name_en")


class ProgramSerializer(LocalizedModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name_ru", read_only=True)

    class Meta:
        model = Program
        fields = ("id", "faculty", "faculty_name", "code", "name", "name_tj", "name_ru", "name_en", "degree", "duration_years")


class UserProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "display_name", "avatar_color")


class TeacherSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    email = serializers.EmailField(write_only=True, required=False)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    faculty_name = serializers.CharField(source="faculty.name_ru", read_only=True)

    class Meta:
        model = Teacher
        fields = ("id", "user", "email", "first_name", "last_name", "password", "employee_id", "faculty", "faculty_name", "position", "phone")

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data.pop("email"),
            password=validated_data.pop("password", None),
            first_name=validated_data.pop("first_name", ""),
            last_name=validated_data.pop("last_name", ""),
            role=User.Role.TEACHER,
        )
        return Teacher.objects.create(user=user, **validated_data)


class GroupSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source="program.name_ru", read_only=True)
    program_name_tj = serializers.CharField(source="program.name_tj", read_only=True)
    program_name_en = serializers.CharField(source="program.name_en", read_only=True)
    student_count = serializers.IntegerField(read_only=True)
    curator_name = serializers.CharField(source="curator.user.display_name", read_only=True, allow_null=True)

    class Meta:
        model = Group
        fields = ("id", "program", "program_name", "program_name_tj", "program_name_en", "code", "admission_year", "course", "curator", "curator_name", "is_active", "student_count")


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"


class SubjectSerializer(LocalizedModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "code", "name", "name_tj", "name_ru", "name_en", "credits")


class StudentMovementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True)

    class Meta:
        model = StudentMovement
        fields = ("id", "kind", "effective_date", "from_group", "to_group", "order_number", "reason", "author_name", "created_at")


class StudentSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    email = serializers.EmailField(write_only=True, required=False)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    group_code = serializers.CharField(source="group.code", read_only=True)
    movements = StudentMovementSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ("id", "user", "email", "first_name", "last_name", "password", "student_id", "group", "group_code", "status", "admission_date", "phone", "movements")

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data.pop("email"),
            password=validated_data.pop("password", None),
            first_name=validated_data.pop("first_name", ""),
            last_name=validated_data.pop("last_name", ""),
            role=User.Role.STUDENT,
        )
        student = Student.objects.create(user=user, **validated_data)
        StudentMovement.objects.create(
            student=student,
            kind=StudentMovement.Kind.ENROLLMENT,
            effective_date=student.admission_date,
            to_group=student.group,
            reason="Initial enrollment",
            author=self.context["request"].user,
        )
        return student
