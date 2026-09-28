# Implementation plan

## Initial audit

The workspace was empty on 26 September 2026. There was no existing application, database, migration history or user data to preserve. The current Orion project was created inside this folder. No code or data was read from or copied from another university-crm project.

## Capability status

| Area | Status | Implemented scope | Remaining product work |
|---|---|---|---|
| Authentication and roles | Working core | Email login, JWT access/refresh, admin/teacher/student roles, backend permissions and frontend route guards | Password recovery needs a university mail/support workflow; refresh-token revocation should be added for production SSO policies |
| Design system | Ready for primary screens | Premium light/dark themes, typography, brand mark, responsive shell, forms, tables, status chips, dialogs, loading/error/empty states, visible focus and reduced motion | Browser regression suite and final screen-reader review |
| Three languages | Ready for primary screens | Tajik, Russian and English navigation, login, dashboards, admissions, schedule, journal, exams, campus and system states; current route is preserved | Translate server validation text and institution-entered content where localized fields are not yet modeled |
| Academic structure | Working core | Faculties, programmes, qualifications, groups, rooms and subjects with admin create forms; teachers, students and movement history APIs | Inline edit/archive actions and bulk student management UI |
| Admissions | Working core | Applicant, documents, immutable status history, controlled transitions, atomic/idempotent enrolment without re-entry | Rich document upload storage and configurable decision templates |
| Excel import | Working core | XLSX/UTF-8 CSV preview, required-field checks, programme/year lookup, duplicate detection, atomic confirmation and import history | Downloadable template and column mapping wizard |
| Curriculum and workload | Working core | Versioned curriculum plans, subject-hour editor, activation workflow and teacher workload assignment UI/API | Workload charts, copy/version assistant and approval rules |
| Schedule | Working core | Role-scoped weekly schedule, admin editor, room/teacher/group overlap detection and creation of real journal sessions | Drag-and-drop planning and recurring exception management |
| Electronic journal | Advanced core | Desktop table, dedicated mobile marking, autosave, keyboard movement, bulk marking, visible save states, idempotency, optimistic locking, confirmation and audit | CSV/PDF export and configurable final-grade formula editor |
| Journal reports | Working core | Day/week/month/semester attendance and grade reports scoped by student, group, offering and subject; student privacy enforced | Saved report presets and printable institutional layouts |
| Closed-semester corrections | Working core | Old/new values, reason, author/time, pending workflow and administrator approval/rejection UI | Multi-step approval chains configurable by university |
| Attendance policy | Working foundation | Configurable thresholds including demo values 35/36/47/48; no unconfirmed administrative consequence is assigned | University must define actions, recipients and escalation policy |
| Exams and transcript | Working core | Exam sheets, idempotent result save, submission/approval, protected corrections and student transcript | Official GPA/letter-grade scale must be configured before calculation/export |
| Learning | Working core | Syllabi/materials, assignments, student submission/resubmission, teacher grading, visual multi-question quiz authoring/player and server scoring | Secure file storage provider and richer quiz question types |
| Finance | Working core | Admin contract creation, payment schedule, confirmed manual payments, balances and student-private access | Debt case automation, receipts, reconciliation and exports |
| HR | Working core | Employee register, document metadata, orders, work logs, admin forms and admin-only permissions | Timesheet report and secure document storage |
| Research | Working core | Coursework/thesis topic editor, supervisor scoping, milestone forms and defence state | Committee/protocol workflow and defence calendar |
| Communication | Working core | Localized announcements, private inbox/composer, read states, notifications and working topbar notification centre | Attachments, conversation threads and scheduled reminder rules |
| Analytics and risk cases | Working foundation | Risk case creation/resolution, responsible user, intervention-note history, role scoping and admin workspace | Configurable risk rules and outcome analytics |
| Library and student services | Working core | Catalogue editor, atomic issue/return desk, student-private loans and localized student information/service cards | Reservations and service-request workflow |
| External integrations | Prepared, inactive | Explicit registry and configuration-required state for Face ID, cameras, SMS, banks, plagiarism and conferences | Provider contracts, credentials, hardware and production adapters |

## Next delivery order

1. Add structure inline edit/archive actions and the library reservation workflow while retaining all current APIs and data.
2. Add secure file storage and richer quiz question types for learning content.
3. Add automated notifications and configurable risk rules.
4. Add official grade-scale configuration, transcript export and report exports.
5. Add downloadable Excel templates, mapping rules and large-import background processing.
6. Run browser visual regression at 390, 768, 1440 and 3840 px when a browser runtime is available.
7. Connect external providers only after the university supplies contracts, credentials and operating rules.

Every stage must keep migration checks, role-isolation tests, the production Django security check and the frontend production build green.
