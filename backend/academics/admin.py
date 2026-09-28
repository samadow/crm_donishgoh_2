from django.contrib import admin

from .models import Faculty, Group, Program, Room, Student, StudentMovement, Subject, Teacher

admin.site.register([Faculty, Program, Teacher, Group, Room, Subject, Student, StudentMovement])

