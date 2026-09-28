from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from academics.models import Faculty, Group, Program, Room, Student, Subject, Teacher
from admissions.models import Applicant, ApplicantDocument, Application, ApplicationStatusHistory
from assessment.models import ExamResult, ExamSheet
from campus.models import (
    Announcement, Assignment, ConfirmedPayment, HRDocument, HROrder, IntegrationEndpoint, InternalMessage, LearningMaterial, LibraryItem,
    Notification, PaymentSchedule, ResearchMilestone, ResearchProject, RiskCase, SelfCheckQuiz,
    StaffEmployee, StudentContract, StudentService, WorkLog,
)
from journal.models import AcademicYear, AttendanceRecord, ClassSession, CourseOffering, Semester, UniversityPolicy
from planning.models import CurriculumPlan, CurriculumSubject, ScheduleEntry, TeacherWorkload

User = get_user_model()


class Command(BaseCommand):
    help = "Create an idempotent demo university with administrator, teacher and student accounts."

    def handle(self, *args, **options):
        today = timezone.localdate()
        admin = self.user("admin@orion.tj", "DemoAdmin!2026", "Мадина", "Каримова", User.Role.ADMIN, is_staff=True, is_superuser=True)
        teacher_user = self.user("teacher@orion.tj", "DemoTeacher!2026", "Фирӯз", "Раҳимов", User.Role.TEACHER)
        student_user = self.user("student@orion.tj", "DemoStudent!2026", "Зуҳро", "Саидова", User.Role.STUDENT)

        faculty, _ = Faculty.objects.update_or_create(
            code="FIT",
            defaults={
                "name_tj": "Факултети технологияҳои иттилоотӣ",
                "name_ru": "Факультет информационных технологий",
                "name_en": "Faculty of Information Technology",
            },
        )
        program, _ = Program.objects.update_or_create(
            code="CS-01",
            defaults={
                "faculty": faculty,
                "name_tj": "Илмҳои компютерӣ",
                "name_ru": "Компьютерные науки",
                "name_en": "Computer Science",
                "degree": Program.Degree.BACHELOR,
                "duration_years": 4,
            },
        )
        teacher, _ = Teacher.objects.update_or_create(
            user=teacher_user,
            defaults={"employee_id": "T-1001", "faculty": faculty, "position": "Старший преподаватель", "phone": "+992 900 00 10 01"},
        )
        group, _ = Group.objects.update_or_create(
            code="CS-23-01",
            defaults={"program": program, "admission_year": 2023, "course": 3, "curator": teacher, "is_active": True},
        )
        subject, _ = Subject.objects.update_or_create(
            code="CS-DB-301",
            defaults={
                "name_tj": "Пойгоҳи додаҳо",
                "name_ru": "Базы данных",
                "name_en": "Databases",
                "credits": 5,
            },
        )
        room, _ = Room.objects.update_or_create(
            code="A-402",
            defaults={"building": "Корпус A", "capacity": 32, "room_type": "computer_lab", "is_accessible": True},
        )

        students = []
        names = [
            (student_user, "S-23001"),
            (("nigina@orion.tj", "Нигина", "Аҳмадова"), "S-23002"),
            (("rustam@orion.tj", "Рустам", "Юсуфӣ"), "S-23003"),
            (("muhammad@orion.tj", "Муҳаммад", "Шарифов"), "S-23004"),
            (("farzona@orion.tj", "Фарзона", "Қодирова"), "S-23005"),
            (("sino@orion.tj", "Сино", "Ғафуров"), "S-23006"),
            (("shahnoza@orion.tj", "Шаҳноза", "Ҷӯраева"), "S-23007"),
            (("daler@orion.tj", "Далер", "Ҳакимов"), "S-23008"),
        ]
        for identity, student_id in names:
            if isinstance(identity, tuple):
                user, _ = User.objects.get_or_create(
                    email=identity[0],
                    defaults={"first_name": identity[1], "last_name": identity[2], "role": User.Role.STUDENT},
                )
                if not user.has_usable_password():
                    user.set_unusable_password()
                    user.save(update_fields=("password",))
            else:
                user = identity
            student, _ = Student.objects.update_or_create(
                user=user,
                defaults={"student_id": student_id, "group": group, "status": Student.Status.ACTIVE, "admission_date": today.replace(year=2023, month=9, day=1)},
            )
            students.append(student)

        academic_year, _ = AcademicYear.objects.update_or_create(
            name=f"{today.year}-{today.year + 1}",
            defaults={"start_date": today.replace(month=9, day=1), "end_date": today.replace(year=today.year + 1, month=6, day=30), "is_current": True},
        )
        semester, _ = Semester.objects.update_or_create(
            academic_year=academic_year,
            number=1,
            defaults={"start_date": academic_year.start_date, "end_date": academic_year.start_date + timedelta(days=120), "status": Semester.Status.OPEN},
        )
        offering, _ = CourseOffering.objects.update_or_create(
            group=group,
            subject=subject,
            teacher=teacher,
            semester=semester,
            defaults={"planned_hours": 72, "is_active": True},
        )
        sessions = []
        topics = ["Реляционная модель", "Нормализация данных", "SQL: выборка и соединения"]
        for offset, topic in zip((0, 2, 7), topics):
            session, _ = ClassSession.objects.update_or_create(
                offering=offering,
                date=today + timedelta(days=offset),
                start_time=time(9, 0),
                defaults={"end_time": time(10, 30), "topic": topic, "session_type": ClassSession.SessionType.PRACTICE, "room": room, "academic_hours": 2},
            )
            sessions.append(session)

        for index, student in enumerate(students[:4]):
            AttendanceRecord.objects.update_or_create(
                session=sessions[0],
                student=student,
                defaults={
                    "status": AttendanceRecord.Status.PRESENT if index != 2 else AttendanceRecord.Status.LATE,
                    "grade": 90 - index * 5,
                    "grade_type": AttendanceRecord.GradeType.DAILY,
                    "comment": "",
                    "is_confirmed": False,
                    "updated_by": teacher_user,
                },
            )
        UniversityPolicy.objects.get_or_create(
            name="Основная политика",
            defaults={"attendance_warning_thresholds": [35, 36, 47, 48], "updated_by": admin},
        )

        applicant, _ = Applicant.objects.update_or_create(
            email="mehrona.applicant@example.tj",
            defaults={
                "first_name": "Меҳрона", "last_name": "Қурбонова", "middle_name": "Ҷамшедовна",
                "birth_date": today.replace(year=today.year - 18, month=5, day=10), "phone": "+992 900 55 44 33",
                "national_id": "DEMO-A-2026", "address": "Душанбе",
            },
        )
        application, _ = Application.objects.update_or_create(
            application_number="APP-DEMO-2026-01",
            defaults={"applicant": applicant, "program": program, "academic_year": academic_year, "status": Application.Status.ACCEPTED, "source": "office", "decision_at": timezone.now(), "decision_reason": "Demo verified application", "assigned_to": admin},
        )
        if not application.status_history.exists():
            ApplicationStatusHistory.objects.create(application=application, from_status="", to_status=Application.Status.ACCEPTED, reason="Demo application prepared", author=admin)
        ApplicantDocument.objects.update_or_create(
            application=application,
            document_type=ApplicantDocument.Type.PASSPORT,
            defaults={"title": "Passport", "identifier": "DEMO-A-2026", "file_name": "passport-demo.pdf", "status": ApplicantDocument.Status.VERIFIED, "verified_by": admin, "verified_at": timezone.now()},
        )

        ScheduleEntry.objects.update_or_create(
            offering=offering,
            weekday=today.weekday(),
            start_time=time(9, 0),
            effective_from=semester.start_date,
            defaults={"end_time": time(10, 30), "room": room, "effective_to": semester.end_date, "is_active": True, "created_by": admin},
        )
        curriculum, _ = CurriculumPlan.objects.update_or_create(
            program=program,
            academic_year=academic_year,
            version=1,
            defaults={"name": "Основной учебный план", "status": CurriculumPlan.Status.ACTIVE, "created_by": admin},
        )
        curriculum_subject, _ = CurriculumSubject.objects.update_or_create(
            plan=curriculum,
            subject=subject,
            semester_number=semester.number,
            defaults={
                "course": group.course,
                "lecture_hours": 24,
                "practice_hours": 24,
                "lab_hours": 0,
                "independent_hours": 72,
                "credits": 5,
                "assessment_type": CurriculumSubject.AssessmentType.EXAM,
            },
        )
        TeacherWorkload.objects.update_or_create(
            teacher=teacher,
            curriculum_subject=curriculum_subject,
            group=group,
            semester=semester,
            defaults={"planned_hours": 48, "assigned_by": admin},
        )

        exam_sheet, _ = ExamSheet.objects.update_or_create(
            offering=offering,
            assessment_type=ExamSheet.Type.EXAM,
            exam_date=semester.end_date,
            defaults={"start_time": time(9, 0), "room": room, "max_score": 100, "passing_score": 50, "status": ExamSheet.Status.APPROVED, "created_by": teacher_user, "approved_by": admin, "approved_at": timezone.now()},
        )
        for index, student in enumerate(students):
            ExamResult.objects.update_or_create(
                sheet=exam_sheet,
                student=student,
                defaults={"score": 92 - index * 4, "grade_label": "A" if index < 3 else "B", "comment": "", "status": ExamResult.Status.APPROVED, "updated_by": teacher_user},
            )

        LearningMaterial.objects.update_or_create(
            offering=offering,
            title="SQL: запросы и соединения",
            defaults={
                "kind": LearningMaterial.Kind.LECTURE,
                "description": "Конспект занятия и практические примеры для текущей темы.",
                "language": "ru",
                "resource_url": "https://www.postgresql.org/docs/current/tutorial.html",
                "published_by": teacher_user,
                "is_published": True,
            },
        )
        Assignment.objects.update_or_create(
            offering=offering,
            title="Спроектировать схему данных",
            defaults={
                "instructions": "Подготовьте нормализованную схему для выбранной предметной области и объясните ключевые решения.",
                "due_at": timezone.now() + timedelta(days=10),
                "max_score": Decimal("100"),
                "created_by": teacher_user,
                "is_published": True,
            },
        )
        SelfCheckQuiz.objects.update_or_create(
            offering=offering,
            title="Самопроверка: нормализация",
            defaults={
                "questions": [{
                    "prompt": "Какая нормальная форма исключает частичные зависимости?",
                    "choices": ["Первая", "Вторая", "Третья"],
                    "correct_index": 1,
                }],
                "is_published": True,
                "created_by": teacher_user,
            },
        )

        contract, _ = StudentContract.objects.update_or_create(
            number="CTR-CS-23001",
            defaults={
                "student": students[0],
                "total_amount": Decimal("12000"),
                "currency": "TJS",
                "signed_date": today.replace(year=2023, month=9, day=1),
                "status": StudentContract.Status.ACTIVE,
            },
        )
        PaymentSchedule.objects.update_or_create(
            contract=contract,
            due_date=today.replace(month=12, day=15),
            defaults={"amount": Decimal("6000"), "note": "Семестровый платёж"},
        )
        ConfirmedPayment.objects.update_or_create(
            reference="DEMO-PAY-23001-01",
            defaults={
                "contract": contract,
                "payment_date": today - timedelta(days=20),
                "amount": Decimal("4500"),
                "note": "Подтверждено бухгалтерией",
                "is_confirmed": True,
                "confirmed_by": admin,
            },
        )

        Announcement.objects.update_or_create(
            title_ru="Неделя проектных консультаций",
            defaults={
                "audience": Announcement.Audience.ALL,
                "title_tj": "Ҳафтаи машваратҳои лоиҳавӣ",
                "title_en": "Project consultation week",
                "body_tj": "Ҷадвали машваратҳоро дар бахши таълим санҷед.",
                "body_ru": "Проверьте расписание консультаций в учебном разделе.",
                "body_en": "Check the consultation schedule in the learning section.",
                "published_by": admin,
                "publish_at": timezone.now() - timedelta(hours=2),
                "is_pinned": True,
            },
        )
        Notification.objects.update_or_create(
            user=student_user,
            kind="assignment",
            title="Новое задание по базам данных",
            defaults={"body": "Срок выполнения указан в разделе обучения.", "link": "/campus"},
        )
        InternalMessage.objects.update_or_create(
            sender=teacher_user,
            recipient=student_user,
            subject="Консультация по курсовой работе",
            defaults={"body": "Подготовьте структуру обзора литературы к следующей консультации."},
        )

        employee, _ = StaffEmployee.objects.update_or_create(
            employee_id="T-1001",
            defaults={
                "user": teacher_user,
                "full_name": teacher_user.display_name,
                "faculty": faculty,
                "department": "Кафедра программной инженерии",
                "position": "Старший преподаватель",
                "hire_date": today.replace(year=today.year - 4, month=8, day=20),
                "status": StaffEmployee.Status.ACTIVE,
            },
        )
        HRDocument.objects.update_or_create(
            employee=employee,
            document_type="employment_contract",
            title="Трудовой договор",
            defaults={"number": "HR-CONTRACT-1001", "issue_date": employee.hire_date, "file_name": ""},
        )
        HROrder.objects.update_or_create(
            number="HR-ORDER-DEMO-01",
            defaults={"employee": employee, "order_type": "appointment", "order_date": employee.hire_date, "summary": "Приём на должность старшего преподавателя", "created_by": admin},
        )
        WorkLog.objects.update_or_create(
            employee=employee,
            date=today,
            defaults={"hours": Decimal("8"), "note": "Учебная и методическая работа", "approved_by": admin},
        )
        project, _ = ResearchProject.objects.update_or_create(
            student=students[0],
            project_type=ResearchProject.Type.COURSEWORK,
            defaults={
                "supervisor": teacher,
                "title": "Оптимизация запросов в университетских информационных системах",
                "status": ResearchProject.Status.IN_PROGRESS,
            },
        )
        ResearchMilestone.objects.update_or_create(
            project=project,
            title="Обзор литературы",
            defaults={"due_date": today + timedelta(days=14), "feedback": ""},
        )
        RiskCase.objects.update_or_create(
            student=students[2],
            category="attendance",
            defaults={
                "severity": "medium",
                "reason": "Требуется беседа по динамике посещаемости; решение назначает ответственный сотрудник.",
                "status": RiskCase.Status.MONITORING,
                "assigned_to": admin,
                "created_by": admin,
            },
        )
        LibraryItem.objects.update_or_create(
            isbn="978-1-4493-7638-4",
            defaults={
                "title": "Designing Data-Intensive Applications",
                "authors": "Martin Kleppmann",
                "publication_year": 2017,
                "total_copies": 5,
                "available_copies": 3,
                "resource_url": "",
            },
        )
        StudentService.objects.update_or_create(
            code="STUDENT-CENTER",
            defaults={
                "title_tj": "Маркази хизматрасонӣ ба донишҷӯён",
                "title_ru": "Центр обслуживания студентов",
                "title_en": "Student service centre",
                "description_tj": "Маълумотномаҳо, аризаҳо ва машварат дар як нуқта.",
                "description_ru": "Справки, заявления и консультации в одной точке.",
                "description_en": "Certificates, requests and guidance in one place.",
                "contact": "Корпус A · кабинет 105",
                "is_active": True,
            },
        )
        for kind, _label in IntegrationEndpoint.Kind.choices:
            IntegrationEndpoint.objects.update_or_create(
                kind=kind,
                defaults={
                    "status": IntegrationEndpoint.Status.CONFIG_REQUIRED,
                    "provider_name": "",
                    "public_note": "",
                    "configuration_schema": {},
                    "updated_by": admin,
                },
            )
        self.stdout.write(self.style.SUCCESS("Demo university is ready."))

    def user(self, email, password, first_name, last_name, role, **flags):
        user, _ = User.objects.update_or_create(
            email=email,
            defaults={"first_name": first_name, "last_name": last_name, "role": role, **flags},
        )
        user.set_password(password)
        user.save(update_fields=("password",))
        return user
