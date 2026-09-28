# Progress

Last updated: 2026-09-27 (Asia/Tashkent)

## Completed

- Created the Django REST Framework and React/TypeScript/Vite platform in the initially empty workspace, with PostgreSQL as the default database and an explicit SQLite demo/test mode.
- Implemented email users, JWT authentication, administrator/teacher/student roles, backend object scoping and frontend route guards.
- Built the premium responsive design system, original campus hero, light/dark themes, reduced motion, visible focus, desktop shell and separate mobile interaction patterns.
- Added complete primary-screen translations for тоҷикӣ, русский and English. Demo data verifies ӣ, ӯ, қ, ғ, ҳ, ҷ.
- Implemented academic structure, student profiles and movement history.
- Added administrator creation forms and directories for faculties, programmes, groups, subjects and rooms.
- Implemented admissions from applicant intake through document/status history to atomic, idempotent enrolment into a group.
- Added real XLSX/CSV import preview with field checks, duplicate checks and a separate atomic confirmation step.
- Implemented curricula, teacher workload APIs and weekly scheduling with group/teacher/room conflict detection.
- Added the administrator curriculum editor for versioned plans, subject hours, plan activation and teacher workload assignments.
- Implemented the electronic journal with bulk marking, autosave, keyboard navigation, mobile cards, idempotency, optimistic versions and server-side role enforcement.
- Added day/week/month/semester journal reports and a closed-semester correction approval screen.
- Implemented exam sheets, approval, correction history and read-only student transcripts.
- Added learning materials, assignments/submissions, server-scored self-check quizzes, finance, HR, research, announcements, private messages, notifications, risk cases, library and student services.
- Added student assignment submission/resubmission, the self-check quiz player with saved results and the teacher assignment grading workspace.
- Added visual multi-question self-check authoring for teachers and administrators; correct answers stay server-side.
- Added administrator finance forms for contracts, payment schedules and manual confirmation of real recorded payments.
- Added administrator forms for the employee register and risk cases, including a real server-side resolution action.
- Added HR document metadata and order forms; file upload is explicitly marked unavailable until secure storage is configured.
- Added research topic/milestone forms and library catalogue/issue forms with atomic available-copy accounting.
- Added risk intervention notes with author/time history inside the administrator workspace.
- Added a working global section search and notification centre.
- Added the private internal message centre with recipient selection, inbox/sent states, read tracking and server-side participant isolation.
- Added an explicit external-integration registry. Face ID, cameras, SMS, banking, plagiarism and conferencing remain in configuration-required state.
- Added secure production defaults when DJANGO_DEBUG=false: HTTPS redirect, secure cookies, HSTS and mandatory non-development secret.
- Expanded idempotent demo data across admissions, schedule, exams, learning, finance, research, risk, library, services and integration states.

## Verification results

- All migrations applied to the local SQLite verification database.
- manage.py makemigrations --check --dry-run: no model changes missing migrations.
- Production manage.py check --deploy with temporary secure environment values: 0 issues.
- All 23 backend tests passed. They cover admissions/import/enrolment, scheduling conflicts, journal concurrency/privacy/reports/approval, exams, learning permissions, private messages, risk controls and atomic library circulation.
- Native XLSX parsing with date cells and UTF-8 CSV import are covered by API tests.
- Frontend TypeScript and Vite production build: passed with 1,591 modules.
- Latest bundle: CSS about 59.5 KB (11.9 KB gzip), JS about 404.4 KB (105.3 KB gzip).
- npm audit: 0 known vulnerabilities across 56 dependencies.
- seed_demo completed successfully twice, confirming idempotent demo setup.
- In-app browser visual QA could not run because this execution environment exposed no browser runtime. Responsive source states and production compilation were checked.

## Known unfinished work

- Structure inline edit/archive actions, library reservations and the research defence committee/protocol workflow remain incomplete.
- Secure learning-file upload still needs an object-storage provider; the current material form records verified external resource links.
- Official GPA and final-grade rules require university-approved scales; the system intentionally does not invent them.
- Attendance thresholds 35/36/47/48 are configurable signals only. Administrative actions remain undefined until the university supplies rules.
- Password recovery needs the university mail or support process.
- Uploaded documents and learning files need a configured object-storage provider.
- External integrations need actual providers, credentials and hardware and are not presented as active.
- Automated visual regression remains pending until a browser runtime is available.

## Exact next step

Add structure inline edit/archive actions and library reservations, then add message attachments, secure learning-file storage and configurable automated notifications. Keep role-isolation tests and the three-language production build green after each screen.
