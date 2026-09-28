from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from academics.views import FacultyViewSet, GroupViewSet, ProgramViewSet, RoomViewSet, StudentViewSet, SubjectViewSet, TeacherViewSet
from admissions.views import AdmissionImportBatchViewSet, ApplicantDocumentViewSet, ApplicantViewSet, ApplicationViewSet
from assessment.views import ExamResultChangeViewSet, ExamResultViewSet, ExamSheetViewSet, TranscriptView
from journal.views import AcademicYearViewSet, AttendanceRecordViewSet, ClassSessionViewSet, CourseOfferingViewSet, JournalChangeViewSet, SemesterViewSet, UniversityPolicyViewSet
from planning.views import CurriculumPlanViewSet, CurriculumSubjectViewSet, ScheduleEntryViewSet, TeacherWorkloadViewSet
from campus.views import (
    AnnouncementViewSet, AssignmentSubmissionViewSet, AssignmentViewSet, CampusOverviewView,
    ConfirmedPaymentViewSet, HRDocumentViewSet, HROrderViewSet, IntegrationEndpointViewSet,
    InternalMessageViewSet, LearningMaterialViewSet, LibraryItemViewSet, LibraryLoanViewSet,
    NotificationViewSet, PaymentScheduleViewSet, QuizAttemptViewSet, ResearchMilestoneViewSet,
    ResearchProjectViewSet, RiskCaseNoteViewSet, RiskCaseViewSet, SelfCheckQuizViewSet,
    StaffEmployeeViewSet, StudentContractViewSet, StudentServiceViewSet, WorkLogViewSet,
)


router = DefaultRouter()
router.register("faculties", FacultyViewSet)
router.register("programs", ProgramViewSet)
router.register("groups", GroupViewSet, basename="group")
router.register("rooms", RoomViewSet)
router.register("subjects", SubjectViewSet)
router.register("students", StudentViewSet, basename="student")
router.register("teachers", TeacherViewSet, basename="teacher")
router.register("academic-years", AcademicYearViewSet)
router.register("semesters", SemesterViewSet)
router.register("offerings", CourseOfferingViewSet, basename="offering")
router.register("sessions", ClassSessionViewSet, basename="session")
router.register("attendance-records", AttendanceRecordViewSet, basename="attendance-record")
router.register("journal-changes", JournalChangeViewSet, basename="journal-change")
router.register("university-policy", UniversityPolicyViewSet, basename="university-policy")
router.register("applicants", ApplicantViewSet)
router.register("applications", ApplicationViewSet, basename="application")
router.register("applicant-documents", ApplicantDocumentViewSet)
router.register("admission-imports", AdmissionImportBatchViewSet, basename="admission-import")
router.register("curriculum-plans", CurriculumPlanViewSet)
router.register("curriculum-subjects", CurriculumSubjectViewSet)
router.register("teacher-workloads", TeacherWorkloadViewSet, basename="teacher-workload")
router.register("schedule-entries", ScheduleEntryViewSet, basename="schedule-entry")
router.register("exam-sheets", ExamSheetViewSet, basename="exam-sheet")
router.register("exam-results", ExamResultViewSet, basename="exam-result")
router.register("exam-result-changes", ExamResultChangeViewSet, basename="exam-result-change")
router.register("learning-materials", LearningMaterialViewSet, basename="learning-material")
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("assignment-submissions", AssignmentSubmissionViewSet, basename="assignment-submission")
router.register("self-check-quizzes", SelfCheckQuizViewSet, basename="self-check-quiz")
router.register("quiz-attempts", QuizAttemptViewSet, basename="quiz-attempt")
router.register("student-contracts", StudentContractViewSet, basename="student-contract")
router.register("payment-schedule", PaymentScheduleViewSet, basename="payment-schedule")
router.register("confirmed-payments", ConfirmedPaymentViewSet, basename="confirmed-payment")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("messages", InternalMessageViewSet, basename="message")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("staff-employees", StaffEmployeeViewSet)
router.register("hr-documents", HRDocumentViewSet)
router.register("hr-orders", HROrderViewSet)
router.register("work-logs", WorkLogViewSet)
router.register("research-projects", ResearchProjectViewSet, basename="research-project")
router.register("research-milestones", ResearchMilestoneViewSet, basename="research-milestone")
router.register("risk-cases", RiskCaseViewSet, basename="risk-case")
router.register("risk-case-notes", RiskCaseNoteViewSet, basename="risk-case-note")
router.register("library-items", LibraryItemViewSet)
router.register("library-loans", LibraryLoanViewSet, basename="library-loan")
router.register("student-services", StudentServiceViewSet)
router.register("integration-endpoints", IntegrationEndpointViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/dashboard/", include("core.urls")),
    path("api/transcript/", TranscriptView.as_view(), name="transcript"),
    path("api/campus-overview/", CampusOverviewView.as_view(), name="campus-overview"),
    path("api/", include(router.urls)),
]
