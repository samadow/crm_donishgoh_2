from django.contrib import admin

from .models import CurriculumPlan, CurriculumSubject, ScheduleEntry, TeacherWorkload

admin.site.register([CurriculumPlan, CurriculumSubject, TeacherWorkload, ScheduleEntry])

