from datetime import date, time

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import Faculty, Group, Program, Room, Subject, Teacher
from journal.models import AcademicYear, CourseOffering, Semester

User = get_user_model()


class ScheduleConflictTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@schedule.tj", password="password-123", role=User.Role.ADMIN)
        teacher_user = User.objects.create_user(email="teacher@schedule.tj", password="password-123", role=User.Role.TEACHER)
        other_teacher_user = User.objects.create_user(email="other@schedule.tj", password="password-123", role=User.Role.TEACHER)
        faculty = Faculty.objects.create(code="ENG", name_tj="Муҳандисӣ", name_ru="Инженерия", name_en="Engineering")
        program = Program.objects.create(faculty=faculty, code="ENG-1", name_tj="Муҳандисӣ", name_ru="Инженерия", name_en="Engineering")
        self.group = Group.objects.create(program=program, code="ENG-01", admission_year=2026, course=1)
        other_group = Group.objects.create(program=program, code="ENG-02", admission_year=2026, course=1)
        self.teacher = Teacher.objects.create(user=teacher_user, employee_id="T-10", faculty=faculty)
        other_teacher = Teacher.objects.create(user=other_teacher_user, employee_id="T-11", faculty=faculty)
        self.room = Room.objects.create(code="201", building="A", capacity=30)
        other_room = Room.objects.create(code="202", building="A", capacity=30)
        subject = Subject.objects.create(code="MATH", name_tj="Риёзӣ", name_ru="Математика", name_en="Mathematics")
        other_subject = Subject.objects.create(code="PHY", name_tj="Физика", name_ru="Физика", name_en="Physics")
        year = AcademicYear.objects.create(name="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
        semester = Semester.objects.create(academic_year=year, number=1, start_date=date(2026, 9, 1), end_date=date(2026, 12, 30))
        self.offering = CourseOffering.objects.create(group=self.group, subject=subject, teacher=self.teacher, semester=semester)
        self.other_offering = CourseOffering.objects.create(group=other_group, subject=other_subject, teacher=other_teacher, semester=semester)
        self.same_teacher_offering = CourseOffering.objects.create(group=other_group, subject=subject, teacher=self.teacher, semester=semester)
        self.other_room = other_room
        self.client.force_authenticate(self.admin)

    def payload(self, offering, room, start="09:00", end="10:30"):
        return {"offering": offering.id, "weekday": 0, "start_time": start, "end_time": end, "room": room.id, "effective_from": "2026-09-01", "effective_to": "2026-12-30", "is_active": True}

    def test_room_conflict_returns_409(self):
        first = self.client.post("/api/schedule-entries/", self.payload(self.offering, self.room), format="json")
        conflict = self.client.post("/api/schedule-entries/", self.payload(self.other_offering, self.room, "10:00", "11:00"), format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(conflict.status_code, status.HTTP_409_CONFLICT)

    def test_teacher_conflict_is_detected_across_rooms(self):
        self.client.post("/api/schedule-entries/", self.payload(self.offering, self.room), format="json")
        conflict = self.client.post("/api/schedule-entries/", self.payload(self.same_teacher_offering, self.other_room, "09:30", "10:15"), format="json")
        self.assertEqual(conflict.status_code, status.HTTP_409_CONFLICT)

    def test_non_overlapping_entry_is_created(self):
        self.client.post("/api/schedule-entries/", self.payload(self.offering, self.room), format="json")
        response = self.client.post("/api/schedule-entries/", self.payload(self.other_offering, self.room, "10:30", "12:00"), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

