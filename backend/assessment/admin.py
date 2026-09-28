from django.contrib import admin

from .models import AssessmentSaveOperation, ExamResult, ExamResultChange, ExamSheet

admin.site.register([ExamSheet, ExamResult, ExamResultChange, AssessmentSaveOperation])

