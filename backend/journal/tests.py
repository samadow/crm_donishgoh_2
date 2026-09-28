from datetime import date, time

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import Faculty, Group, Program, Student, Subject, Teacher
from journal.models import AcademicYear, AttendanceRecord, ClassSession, CourseOffering, JournalChange, Semester

User = get_user_model()


class JournalApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.tj", password="password-123", role=User.Role.ADMIN)
        self.teacher_user = User.objects.create_user(email="teacher@test.tj", password="password-123", role=User.Role.TEACHER)
        self.student_user = User.objects.create_user(email="student@test.tj", password="password-123", first_name="Зуҳро", last_name="Саидова", role=User.Role.STUDENT)
        self.other_user = User.objects.create_user(email="other@test.tj", password="password-123", first_name="Далер", last_name="Ҳакимов", role=User.Role.STUDENT)
        faculty = Faculty.objects.create(code="FIT", name_tj="Технология", name_ru="Технологии", name_en="Technology")
        program = Program.objects.create(faculty=faculty, code="CS", name_tj="Илмҳои компютерӣ", name_ru="Компьютерные науки", name_en="Computer Science")
        self.teacher = Teacher.objects.create(user=self.teacher_user, employee_id="T-1", faculty=faculty)
        self.group = Group.objects.create(program=program, code="CS-01", admission_year=2024, course=2)
        self.student = Student.objects.create(user=self.student_user, student_id="S-1", group=self.group, admission_date=date(2024, 9, 1))
        self.other_student = Student.objects.create(user=self.other_user, student_id="S-2", group=self.group, admission_date=date(2024, 9, 1))
        subject = Subject.objects.create(code="DB", name_tj="Пойгоҳи додаҳо", name_ru="Базы данных", name_en="Databases")
        academic_year = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30), is_current=True)
        self.semester = Semester.objects.create(academic_year=academic_year, number=1, start_date=date(2026, 9, 1), end_date=date(2026, 12, 30))
        self.offering = CourseOffering.objects.create(group=self.group, subject=subject, teacher=self.teacher, semester=self.semester)
        self.session = ClassSession.objects.create(offering=self.offering, date=date(2026, 9, 26), start_time=time(9), end_time=time(10, 30), topic="Transactions")

    def bulk_mark(self, user, entries, key="request-1"):
        self.client.force_authenticate(user)
        return self.client.post(
            f"/api/sessions/{self.session.id}/bulk-mark/",
            {"entries": entries},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

    def test_bulk_save_is_idempotent(self):
        entry = {"student_id": self.student.id, "status": "present", "grade": "88", "version": 0}
        first = self.bulk_mark(self.teacher_user, [entry])
        replay = self.bulk_mark(self.teacher_user, [entry])

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertTrue(replay.data["idempotent_replay"])
        self.assertEqual(AttendanceRecord.objects.count(), 1)

    def test_stale_version_returns_conflict_without_overwrite(self):
        record = AttendanceRecord.objects.create(session=self.session, student=self.student, status="present", updated_by=self.teacher_user)
        accepted = self.bulk_mark(self.teacher_user, [{"student_id": self.student.id, "status": "late", "version": record.version}], "request-2")
        rejected = self.bulk_mark(self.teacher_user, [{"student_id": self.student.id, "status": "absent", "version": record.version}], "request-3")

        self.assertEqual(accepted.status_code, status.HTTP_200_OK)
        self.assertEqual(rejected.status_code, status.HTTP_409_CONFLICT)
        record.refresh_from_db()
        self.assertEqual(record.status, "late")

    def test_student_reads_only_own_record_and_cannot_write(self):
        AttendanceRecord.objects.create(session=self.session, student=self.student, status="present", updated_by=self.teacher_user)
        AttendanceRecord.objects.create(session=self.session, student=self.other_student, status="absent", updated_by=self.teacher_user)
        self.client.force_authenticate(self.student_user)

        response = self.client.get("/api/attendance-records/")
        forbidden = self.bulk_mark(self.student_user, [{"student_id": self.student.id, "status": "absent", "version": 1}], "request-4")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["student"], self.student.id)
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_closed_semester_change_is_queued_for_approval(self):
        self.semester.status = Semester.Status.CLOSED
        self.semester.save(update_fields=("status",))
        record = AttendanceRecord.objects.create(
            session=self.session,
            student=self.student,
            status="present",
            is_confirmed=True,
            updated_by=self.teacher_user,
        )

        response = self.bulk_mark(
            self.teacher_user,
            [{"student_id": self.student.id, "status": "absent", "version": record.version, "reason": "Correction after verification"}],
            "request-5",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pending_approval"], 1)
        record.refresh_from_db()
        self.assertEqual(record.status, "present")
        change = JournalChange.objects.get(record=record, status=JournalChange.Status.PENDING)

        self.client.force_authenticate(self.admin)
        approved = self.client.post(f"/api/journal-changes/{change.id}/approve/", {}, format="json")
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        record.refresh_from_db()
        change.refresh_from_db()
        self.assertEqual(record.status, "absent")
        self.assertEqual(record.version, 2)
        self.assertEqual(change.status, JournalChange.Status.APPROVED)
        self.assertEqual(change.reviewer, self.admin)

    def test_period_report_aggregates_hours_and_keeps_student_private(self):
        AttendanceRecord.objects.create(session=self.session, student=self.student, status="present", grade=90, updated_by=self.teacher_user)
        AttendanceRecord.objects.create(session=self.session, student=self.other_student, status="absent", grade=40, updated_by=self.teacher_user)
        endpoint = f"/api/attendance-records/report/?period=day&date=2026-09-26&offering={self.offering.id}"

        self.client.force_authenticate(self.teacher_user)
        teacher_report = self.client.get(endpoint)
        self.assertEqual(teacher_report.status_code, status.HTTP_200_OK)
        self.assertEqual(len(teacher_report.data["students"]), 2)
        self.assertEqual(teacher_report.data["overall"]["present_hours"], self.session.academic_hours)
        self.assertEqual(teacher_report.data["overall"]["absent_hours"], self.session.academic_hours)

        self.client.force_authenticate(self.student_user)
        student_report = self.client.get(endpoint)
        self.assertEqual(len(student_report.data["students"]), 1)
        self.assertEqual(student_report.data["students"][0]["student_id"], self.student.id)
