# Orion University Platform

Orion is a university information system built with Django REST Framework, PostgreSQL, React, TypeScript and Vite. It joins admissions, the academic structure, schedules, the electronic journal, exams, learning, finance, HR, research, communication, analytics, library and student services in one role-aware interface.

The interface works in тоҷикӣ, русский and English. The seed data and translations include ӣ, ӯ, қ, ғ, ҳ and ҷ.

## Implemented product areas

- JWT login and refresh with administrator, teacher and student roles.
- Role dashboards with real data, today’s classes and attention signals.
- Admissions workflow, document states, immutable history and enrolment without re-entering applicant data.
- XLSX and UTF-8 CSV import with preview, validation, duplicate detection and atomic confirmation.
- Administrator directories/create forms for faculties, programmes, groups, rooms and subjects; teachers, students and movement history APIs.
- Curriculum plan editor, subject-hour planning, teacher workload assignment and a weekly schedule with room, teacher and group conflict checks.
- Electronic journal with attendance, grade types, comments, bulk marking, keyboard navigation and a dedicated mobile marking layout.
- Autosave feedback, idempotency keys, optimistic versions and conflict recovery.
- Confirmed-entry audit with old/new values, reason, author and time. Closed-semester changes enter an administrator approval queue.
- Reports by day, week, month and semester. Student data stays private and read-only.
- Configurable missed-hour thresholds. Demo thresholds are 35, 36, 47 and 48 hours; no administrative consequence is assigned without an approved university rule.
- Exam sheets, approval, controlled corrections and a read-only student transcript.
- Materials, syllabi, student assignment submission/resubmission, teacher grading and server-scored self-check quizzes with a student player.
- Administrator contract/payment forms, payment schedules, confirmed manual payments and student-private balances.
- Employee register, HR document metadata, orders and work logs with protected administrator forms.
- Coursework/thesis topic and milestone forms with supervisor scoping.
- Localized announcements, private inbox/composer with read states, real notifications and topbar section search.
- Risk case creation/resolution, an atomic library catalogue/issue/return workflow and a localized student service directory.
- Light/dark themes, reduced motion, visible focus and responsive layouts for mobile, laptop and wide screens.
- Original generated campus artwork with optimized desktop and mobile WebP variants.

Face ID, cameras, SMS, bank payments, plagiarism checks and online conferences are registered as external integrations in configuration-required state. They do not pretend to be active.

## Requirements

- Windows PowerShell
- Python 3.13
- Node.js 20.19 or newer and npm
- PostgreSQL 16 or newer for the standard setup

Docker is optional and is only used as a convenient PostgreSQL host.

## Windows PowerShell: standard PostgreSQL setup

Create a PostgreSQL user and database in psql while signed in as a PostgreSQL administrator:

~~~sql
CREATE USER university WITH PASSWORD 'university';
CREATE DATABASE university OWNER university;
~~~

Prepare the backend:

~~~powershell
cd C:\path\to\ss
Copy-Item .env.example .env
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
~~~

In a second PowerShell window:

~~~powershell
cd C:\path\to\ss\frontend
npm.cmd install
npm.cmd run dev
~~~

Open http://127.0.0.1:5173.

## Windows PowerShell: quick SQLite evaluation

PostgreSQL remains the default. SQLite is available for a local evaluation and automated checks:

~~~powershell
cd C:\path\to\ss
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:USE_SQLITE = "true"
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
~~~

Run the same frontend commands from the previous section in a second window.

## Optional Docker for PostgreSQL

~~~powershell
cd C:\path\to\ss
Copy-Item .env.example .env
docker compose up -d postgres
~~~

Then run migrations, seed_demo and runserver natively with PowerShell.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Administrator | admin@orion.tj | DemoAdmin!2026 |
| Teacher | teacher@orion.tj | DemoTeacher!2026 |
| Student | student@orion.tj | DemoStudent!2026 |

seed_demo is idempotent and resets these three demo passwords to the values above.

## Applicant import format

The admissions page accepts .xlsx and UTF-8 .csv. It validates the file before showing the confirmation button.

Required columns:

- application_number
- first_name
- last_name
- birth_date
- email
- phone
- program_code
- academic_year

Optional columns:

- middle_name
- national_id
- address

Dates can use YYYY-MM-DD, DD.MM.YYYY or native Excel date cells. The preview rejects duplicate emails, document numbers and application numbers before any record is created. Russian and Tajik header aliases are also accepted.

## Verification commands

~~~powershell
cd C:\path\to\ss
$env:USE_SQLITE = "true"
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend\manage.py test admissions planning assessment journal campus --noinput
cd frontend
npm.cmd run build
npm.cmd audit
~~~

For a production security check, set DJANGO_DEBUG=false, a long random DJANGO_SECRET_KEY and the real host before running manage.py check --deploy. Production defaults enable HTTPS redirect, secure cookies and HSTS. DJANGO_TRUST_PROXY_HTTPS must only be enabled behind a trusted proxy that overwrites X-Forwarded-Proto.

## Main API entry points

- POST /api/auth/login/
- POST /api/auth/refresh/
- GET/PATCH /api/auth/me/
- GET /api/dashboard/
- /api/faculties/, /api/programs/, /api/groups/, /api/students/, /api/teachers/
- /api/applications/ and POST /api/applications/{id}/enroll/
- POST /api/admission-imports/preview/ and POST /api/admission-imports/{id}/commit/
- /api/schedule-entries/
- GET /api/sessions/{id}/records/
- POST /api/sessions/{id}/bulk-mark/ with an Idempotency-Key header
- GET /api/attendance-records/report/
- GET /api/journal-changes/ and administrator approval/rejection actions
- /api/exam-sheets/, /api/exam-results/ and GET /api/transcript/
- /api/learning-materials/, /api/assignments/, /api/self-check-quizzes/
- /api/student-contracts/, /api/confirmed-payments/
- /api/announcements/, /api/messages/, /api/notifications/
- /api/staff-employees/, /api/research-projects/, /api/risk-cases/
- /api/library-items/, /api/student-services/, /api/integration-endpoints/

See IMPLEMENTATION_PLAN.md for module status and PROGRESS.md for verified results and the exact next step.
