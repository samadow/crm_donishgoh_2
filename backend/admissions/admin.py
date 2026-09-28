from django.contrib import admin

from .models import AdmissionImportBatch, Applicant, ApplicantDocument, Application, ApplicationStatusHistory, EnrollmentResult

admin.site.register([AdmissionImportBatch, Applicant, ApplicantDocument, Application, ApplicationStatusHistory, EnrollmentResult])
