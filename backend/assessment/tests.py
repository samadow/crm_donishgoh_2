from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import Faculty, Group, Program, Student, Subject, Teacher
from journal.models import AcademicYear, CourseOffering, Semester
from .models import ExamResult, ExamResultChange

User = get_user_model()


class AssessmentWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@exam.tj", password="password-123", role=User.Role.ADMIN)
        self.teacher_user = User.objects.create_user(email="teacher@exam.tj", password="password-123", role=User.Role.TEACHER)
        self.student_user = User.objects.create_user(email="student@exam.tj", password="password-123", first_name="Шаҳноза", last_name="Ҷӯраева", role=User.Role.STUDENT)
        faculty = Faculty.objects.create(code="SCI", name_tj="Илм", name_ru="Наука", name_en="Science")
        program = Program.objects.create(faculty=faculty, code="SCI-1", name_tj="Илм", name_ru="Наука", name_en="Science")
        teacher = Teacher.objects.create(user=self.teacher_user, employee_id="T-20", faculty=faculty)
        group = Group.objects.create(program=program, code="SCI-01", admission_year=2026, course=1)
        self.student = Student.objects.create(user=self.student_user, student_id="S-20", group=group, admission_date=date(2026, 9, 1))
        subject = Subject.objects.create(code="CHEM", name_tj="Химия", name_ru="Химия", name_en="Chemistry", credits=4)
        year = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
        semester = Semester.objects.create(academic_year=year, number=1, start_date=date(2026, 9, 1), end_date=date(2026, 12, 30))
        self.offering = CourseOffering.objects.create(group=group, subject=subject, teacher=teacher, semester=semester)

    def test_approved_result_appears_in_student_transcript_and_correction_is_reviewed(self):
        self.client.force_authenticate(self.teacher_user)
        sheet_response = self.client.post("/api/exam-sheets/", {"offering": self.offering.id, "assessment_type": "exam", "exam_date": "2026-12-20", "max_score": "100", "passing_score": "50"}, format="json")
        self.assertEqual(sheet_response.status_code, status.HTTP_201_CREATED)
        sheet_id = sheet_response.data["id"]
        saved = self.client.post(f"/api/exam-sheets/{sheet_id}/save-results/", {"entries": [{"student_id": self.student.id, "score": "86", "grade_label": "B", "version": 0}]}, format="json", HTTP_IDEMPOTENCY_KEY="exam-save-1")
        self.assertEqual(saved.status_code, status.HTTP_200_OK)
        submitted = self.client.post(f"/api/exam-sheets/{sheet_id}/submit/", {}, format="json")
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(self.admin)
        approved = self.client.post(f"/api/exam-sheets/{sheet_id}/approve/", {}, format="json")
        self.assertEqual(approved.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.student_user)
        transcript = self.client.get("/api/transcript/")
        self.assertEqual(transcript.status_code, status.HTTP_200_OK)
        self.assertEqual(len(transcript.data["records"]), 1)
        self.assertEqual(transcript.data["records"][0]["score"], "86.00")

        result = ExamResult.objects.get(sheet_id=sheet_id, student=self.student)
        self.client.force_authenticate(self.teacher_user)
        correction = self.client.post(f"/api/exam-sheets/{sheet_id}/save-results/", {"entries": [{"student_id": self.student.id, "score": "91", "grade_label": "A", "version": result.version, "reason": "Verified calculation"}]}, format="json", HTTP_IDEMPOTENCY_KEY="exam-save-2")
        self.assertEqual(correction.status_code, status.HTTP_200_OK)
        change = ExamResultChange.objects.get(result=result, status=ExamResultChange.Status.PENDING)
        self.client.force_authenticate(self.admin)
        reviewed = self.client.post(f"/api/exam-result-changes/{change.id}/approve/", {}, format="json")
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK)
        result.refresh_from_db()
        self.assertEqual(str(result.score), "91.00")

