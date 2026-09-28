from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from openpyxl import Workbook

from academics.models import Faculty, Group, Program, Student, StudentMovement
from journal.models import AcademicYear
from .models import Applicant, Application, ApplicationStatusHistory, EnrollmentResult

User = get_user_model()


class AdmissionWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@admission.tj", password="password-123", role=User.Role.ADMIN)
        self.teacher = User.objects.create_user(email="teacher@admission.tj", password="password-123", role=User.Role.TEACHER)
        faculty = Faculty.objects.create(code="MED", name_tj="Тиб", name_ru="Медицина", name_en="Medicine")
        self.program = Program.objects.create(faculty=faculty, code="MED-01", name_tj="Кори табобатӣ", name_ru="Лечебное дело", name_en="Medicine")
        self.group = Group.objects.create(program=self.program, code="MED-26-01", admission_year=2026, course=1)
        self.year = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30), is_current=True)
        self.client.force_authenticate(self.admin)
        application_response = self.client.post("/api/applications/intake/", {
            "applicant": {
                "first_name": "Меҳрона", "last_name": "Қурбонова", "middle_name": "Ҷамшедовна",
                "birth_date": "2008-05-10", "email": "applicant@example.tj", "phone": "+992900001122", "national_id": "A1234567",
            },
            "program": self.program.id, "academic_year": self.year.id, "application_number": "APP-2026-0001", "source": "office",
        }, format="json")
        self.assertEqual(application_response.status_code, status.HTTP_201_CREATED)
        self.applicant_id = application_response.data["applicant"]
        self.application_id = application_response.data["id"]

    def transition(self, target, reason=""):
        return self.client.post(f"/api/applications/{self.application_id}/transition/", {"status": target, "reason": reason}, format="json")

    def test_complete_enrollment_is_atomic_and_idempotent(self):
        for target in ("submitted", "under_review", "documents_verified", "accepted"):
            response = self.transition(target, "Verified by admissions")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        payload = {"group": self.group.id, "order_number": "ORDER-77", "temporary_password": "Temporary!2026"}
        enrolled = self.client.post(f"/api/applications/{self.application_id}/enroll/", payload, format="json")
        replay = self.client.post(f"/api/applications/{self.application_id}/enroll/", payload, format="json")

        self.assertEqual(enrolled.status_code, status.HTTP_200_OK)
        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertTrue(replay.data["idempotent_replay"])
        application = Application.objects.get(pk=self.application_id)
        self.assertEqual(application.status, Application.Status.ENROLLED)
        self.assertEqual(Student.objects.filter(user__email="applicant@example.tj").count(), 1)
        self.assertEqual(StudentMovement.objects.filter(student__user__email="applicant@example.tj", kind=StudentMovement.Kind.ENROLLMENT).count(), 1)
        self.assertEqual(EnrollmentResult.objects.filter(application=application).count(), 1)
        self.assertGreaterEqual(ApplicationStatusHistory.objects.filter(application=application).count(), 6)

    def test_non_admin_cannot_access_admissions(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.get("/api/applications/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_transition_does_not_change_application(self):
        response = self.transition("accepted")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Application.objects.get(pk=self.application_id).status, Application.Status.DRAFT)

    def test_csv_import_previews_then_commits_once(self):
        content = (
            "application_number,first_name,last_name,birth_date,email,phone,national_id,program_code,academic_year\n"
            "APP-2026-0002,Зебо,Ҳакимова,2008-04-11,zebo.import@example.tj,+992900000055,B7654321,MED-01,2026-2027\n"
        ).encode("utf-8")
        upload = SimpleUploadedFile("applicants.csv", content, content_type="text/csv")
        preview = self.client.post("/api/admission-imports/preview/", {"file": upload}, format="multipart")
        self.assertEqual(preview.status_code, status.HTTP_201_CREATED)
        self.assertEqual(preview.data["valid_count"], 1)
        self.assertEqual(preview.data["error_count"], 0)

        endpoint = f"/api/admission-imports/{preview.data['id']}/commit/"
        committed = self.client.post(endpoint, {}, format="json")
        replay = self.client.post(endpoint, {}, format="json")
        self.assertEqual(committed.status_code, status.HTTP_200_OK)
        self.assertTrue(replay.data["idempotent_replay"])
        self.assertEqual(Application.objects.filter(application_number="APP-2026-0002").count(), 1)

    def test_import_preview_reports_duplicates_without_writing(self):
        content = (
            "application_number,first_name,last_name,birth_date,email,phone,program_code,academic_year\n"
            "APP-2026-0003,Меҳрона,Дигар,2008-04-11,applicant@example.tj,+992900000066,MED-01,2026-2027\n"
        ).encode("utf-8")
        upload = SimpleUploadedFile("duplicates.csv", content, content_type="text/csv")
        preview = self.client.post("/api/admission-imports/preview/", {"file": upload}, format="multipart")
        self.assertEqual(preview.status_code, status.HTTP_201_CREATED)
        self.assertEqual(preview.data["error_count"], 1)
        self.assertIn("duplicate", {item["code"] for item in preview.data["rows"][0]["errors"]})
        self.assertEqual(Application.objects.filter(application_number="APP-2026-0003").count(), 0)

    def test_xlsx_preview_reads_native_dates(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["application_number", "first_name", "last_name", "birth_date", "email", "phone", "program_code", "academic_year"])
        sheet.append(["APP-2026-0004", "Ситора", "Ғафурова", date(2008, 3, 12), "sitora.import@example.tj", "+992900000077", "MED-01", "2026-2027"])
        content = BytesIO()
        workbook.save(content)
        workbook.close()
        upload = SimpleUploadedFile(
            "applicants.xlsx",
            content.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        preview = self.client.post("/api/admission-imports/preview/", {"file": upload}, format="multipart")
        self.assertEqual(preview.status_code, status.HTTP_201_CREATED)
        self.assertEqual(preview.data["valid_count"], 1)
        self.assertEqual(preview.data["rows"][0]["data"]["birth_date"], "2008-03-12")
