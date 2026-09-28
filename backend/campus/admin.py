from django.contrib import admin

from .models import *

admin.site.register([
    LearningMaterial, Assignment, AssignmentSubmission, SelfCheckQuiz, QuizAttempt,
    StudentContract, PaymentSchedule, ConfirmedPayment, Announcement, InternalMessage, Notification,
    StaffEmployee, HRDocument, HROrder, WorkLog, ResearchProject, ResearchMilestone,
    RiskCase, RiskCaseNote, LibraryItem, LibraryLoan, StudentService, IntegrationEndpoint,
])

