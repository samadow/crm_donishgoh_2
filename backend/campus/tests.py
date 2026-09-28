from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import Faculty, Group, Program, Student, Subject, Teacher
from journal.models import AcademicYear, CourseOffering, Semester
from .models import Assignment, AssignmentSubmission, IntegrationEndpoint, InternalMessage, LearningMaterial, LibraryItem, RiskCase, SelfCheckQuiz, StudentContract

User = get_user_model()


class CampusModulePermissionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@campus.tj", password="password-123", role=User.Role.ADMIN)
        self.teacher_user = User.objects.create_user(email="teacher@campus.tj", password="password-123", role=User.Role.TEACHER)
        self.student_user = User.objects.create_user(email="student@campus.tj", password="password-123", role=User.Role.STUDENT)
        self.other_student_user = User.objects.create_user(email="other@campus.tj", password="password-123", role=User.Role.STUDENT)
        faculty = Faculty.objects.create(code="ECO", name_tj="Иқтисод", name_ru="Экономика", name_en="Economics")
        program = Program.objects.create(faculty=faculty, code="ECO-1", name_tj="Иқтисод", name_ru="Экономика", name_en="Economics")
        teacher = Teacher.objects.create(user=self.teacher_user, employee_id="T-30", faculty=faculty)
        group = Group.objects.create(program=program, code="ECO-01", admission_year=2026, course=1)
        other_group = Group.objects.create(program=program, code="ECO-02", admission_year=2026, course=1)
        self.student = Student.objects.create(user=self.student_user, student_id="S-30", group=group, admission_date=date(2026, 9, 1))
        self.other_student = Student.objects.create(user=self.other_student_user, student_id="S-31", group=other_group, admission_date=date(2026, 9, 1))
        subject = Subject.objects.create(code="MICRO", name_tj="Микроиқтисод", name_ru="Микроэкономика", name_en="Microeconomics")
        year = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
        semester = Semester.objects.create(academic_year=year, number=1, start_date=date(2026, 9, 1), end_date=date(2026, 12, 30))
        self.offering = CourseOffering.objects.create(group=group, subject=subject, teacher=teacher, semester=semester)
        other_offering = CourseOffering.objects.create(group=other_group, subject=subject, teacher=teacher, semester=semester)
        LearningMaterial.objects.create(offering=self.offering, kind="lecture", title="Elasticity", published_by=self.teacher_user, is_published=True)
        LearningMaterial.objects.create(offering=other_offering, kind="lecture", title="Other group", published_by=self.teacher_user, is_published=True)
        self.quiz = SelfCheckQuiz.objects.create(
            offering=self.offering,
            title="Demand self-check",
            questions=[{"prompt": "Demand rises when?", "choices": ["Price falls", "Price rises"], "correct_index": 0}],
            is_published=True,
            created_by=self.teacher_user,
        )
        self.assignment = Assignment.objects.create(
            offering=self.offering,
            title="Demand analysis",
            instructions="Submit an explanation.",
            due_at=timezone.now() + timedelta(days=7),
            max_score=Decimal("100"),
            created_by=self.teacher_user,
            is_published=True,
        )
        self.risk_case = RiskCase.objects.create(
            student=self.student,
            category="attendance",
            severity="medium",
            reason="Needs follow-up",
            created_by=self.admin,
        )
        StudentContract.objects.create(student=self.student, number="C-30", total_amount=Decimal("10000"), signed_date=date(2026, 9, 1))
        StudentContract.objects.create(student=self.other_student, number="C-31", total_amount=Decimal("12000"), signed_date=date(2026, 9, 1))
        IntegrationEndpoint.objects.create(kind=IntegrationEndpoint.Kind.SMS)

    def test_student_content_is_group_scoped_and_quiz_answers_are_hidden(self):
        self.client.force_authenticate(self.student_user)
        materials = self.client.get("/api/learning-materials/")
        quizzes = self.client.get("/api/self-check-quizzes/")
        attempt = self.client.post(f"/api/self-check-quizzes/{self.quiz.id}/submit/", {"answers": [0]}, format="json")

        self.assertEqual(materials.data["count"], 1)
        self.assertEqual(quizzes.data["count"], 1)
        self.assertNotIn("correct_index", quizzes.data["results"][0]["public_questions"][0])
        self.assertEqual(attempt.status_code, status.HTTP_200_OK)
        self.assertEqual(attempt.data["correct_count"], 1)

    def test_finance_is_private_to_student(self):
        self.client.force_authenticate(self.student_user)
        response = self.client.get("/api/student-contracts/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["number"], "C-30")

        self.client.force_authenticate(self.teacher_user)
        response = self.client.get("/api/student-contracts/")
        self.assertEqual(response.data["count"], 0)

    def test_external_integration_registry_is_admin_only(self):
        self.client.force_authenticate(self.student_user)
        forbidden = self.client.get("/api/integration-endpoints/")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        allowed = self.client.get("/api/integration-endpoints/")
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(allowed.data["results"][0]["status"], IntegrationEndpoint.Status.CONFIG_REQUIRED)

    def test_student_cannot_grade_or_remove_submitted_work(self):
        self.client.force_authenticate(self.student_user)
        invalid = self.client.post(
            "/api/assignment-submissions/",
            {"assignment": self.assignment.id, "text": "Answer", "status": "graded", "score": "100"},
            format="json",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        created = self.client.post(
            "/api/assignment-submissions/",
            {"assignment": self.assignment.id, "text": "Answer", "status": "submitted"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(created.data["score"])
        self.assertEqual(self.client.delete(f"/api/assignment-submissions/{created.data['id']}/").status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_rewrite_risk_case(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.patch(
            f"/api/risk-cases/{self.risk_case.id}/",
            {"status": "resolved"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assigned_teacher_grades_submitted_work(self):
        self.client.force_authenticate(self.student_user)
        created = self.client.post(
            "/api/assignment-submissions/",
            {"assignment": self.assignment.id, "text": "Reviewed answer", "status": "submitted"},
            format="json",
        )
        self.client.force_authenticate(self.teacher_user)
        graded = self.client.patch(
            f"/api/assignment-submissions/{created.data['id']}/",
            {"score": "87", "feedback": "Good structure", "status": "graded"},
            format="json",
        )
        self.assertEqual(graded.status_code, status.HTTP_200_OK)
        submission = AssignmentSubmission.objects.get(pk=created.data["id"])
        self.assertEqual(submission.status, AssignmentSubmission.Status.GRADED)
        self.assertEqual(submission.graded_by, self.teacher_user)

    def test_internal_message_is_private_and_only_recipient_marks_read(self):
        self.client.force_authenticate(self.student_user)
        created = self.client.post(
            "/api/messages/",
            {"recipient": self.teacher_user.id, "subject": "Consultation", "body": "May I clarify the assignment?", "sender": self.other_student_user.id},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        message = InternalMessage.objects.get(pk=created.data["id"])
        self.assertEqual(message.sender, self.student_user)
        self.assertEqual(self.client.post(f"/api/messages/{message.id}/mark-read/", {}, format="json").status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.other_student_user)
        self.assertEqual(self.client.get("/api/messages/").data["count"], 0)
        self.client.force_authenticate(self.teacher_user)
        self.assertEqual(self.client.get("/api/messages/").data["count"], 1)
        self.assertEqual(self.client.post(f"/api/messages/{message.id}/mark-read/", {}, format="json").status_code, status.HTTP_200_OK)

    def test_library_circulation_updates_available_copies_atomically(self):
        item = LibraryItem.objects.create(title="Database Systems", authors="A. Author", total_copies=1, available_copies=1)
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/library-loans/",
            {"item": item.id, "student": self.student.id, "borrowed_at": "2026-09-01", "due_at": "2026-09-15"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        item.refresh_from_db()
        self.assertEqual(item.available_copies, 0)
        unavailable = self.client.post(
            "/api/library-loans/",
            {"item": item.id, "student": self.other_student.id, "borrowed_at": "2026-09-02", "due_at": "2026-09-16"},
            format="json",
        )
        self.assertEqual(unavailable.status_code, status.HTTP_400_BAD_REQUEST)
        returned = self.client.patch(f"/api/library-loans/{created.data['id']}/", {"returned_at": "2026-09-10"}, format="json")
        self.assertEqual(returned.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.available_copies, 1)
