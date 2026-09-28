from django.contrib import admin

from .models import AcademicYear, AttendanceRecord, ClassSession, CourseOffering, JournalChange, SaveOperation, Semester, UniversityPolicy

admin.site.register([AcademicYear, Semester, UniversityPolicy, CourseOffering, ClassSession, AttendanceRecord, JournalChange, SaveOperation])

