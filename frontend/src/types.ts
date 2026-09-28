export type Role = "admin" | "teacher" | "student";
export type Language = "tj" | "ru" | "en";

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  role: Role;
  preferred_language: Language;
  avatar_color: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Offering {
  id: number;
  group: number;
  group_code: string;
  subject: number;
  subject_name: string;
  subject_name_tj: string;
  subject_name_en: string;
  teacher: number;
  teacher_name: string;
  semester: number;
  semester_label: string;
  planned_hours: number;
  is_active: boolean;
  student_count: number;
}

export interface ClassSession {
  id: number;
  offering: number;
  offering_detail: Offering;
  date: string;
  start_time: string;
  end_time: string;
  topic: string;
  session_type: string;
  room: number | null;
  room_label: string;
  academic_hours: number;
  version: number;
  record_count: number;
}

export interface StudentSummary {
  id: number;
  user: User;
  student_id: string;
  group: number;
  group_code: string;
  status: string;
  admission_date: string;
}

export type AttendanceStatus = "unmarked" | "present" | "absent" | "late" | "excused";

export interface AttendanceRecord {
  id?: number;
  session: number;
  student: number;
  student_detail: StudentSummary;
  status: AttendanceStatus;
  grade: string | null;
  grade_type: "daily" | "control" | "independent" | "exam";
  comment: string;
  is_confirmed: boolean;
  version: number;
  updated_by_name?: string;
  updated_at?: string;
  pending?: boolean;
}

export interface DashboardData {
  role: Role;
  stats: Record<string, number | null>;
  today: ClassSession[];
  alerts: Array<Record<string, string | number>>;
}

export interface Group {
  id: number;
  program: number;
  code: string;
  program_name: string;
  program_name_tj: string;
  program_name_en: string;
  course: number;
  admission_year: number;
  curator_name: string | null;
  student_count: number;
  is_active: boolean;
}

export interface Faculty {
  id: number;
  code: string;
  name: string;
}

export interface Program {
  id: number;
  code: string;
  name: string;
  name_tj: string;
  name_ru: string;
  name_en: string;
  faculty: number;
}

export interface AcademicYear {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

export interface Applicant {
  id: number;
  first_name: string;
  last_name: string;
  middle_name: string;
  display_name: string;
  birth_date: string;
  email: string;
  phone: string;
  national_id: string;
}

export interface ApplicationHistory {
  id: number;
  from_status: string;
  to_status: string;
  reason: string;
  author_name: string;
  created_at: string;
}

export interface AdmissionApplication {
  id: number;
  applicant: number;
  applicant_detail: Applicant;
  program: number;
  program_name: string;
  program_name_tj: string;
  program_name_en: string;
  academic_year: number;
  academic_year_name: string;
  application_number: string;
  status: string;
  source: string;
  version: number;
  status_history: ApplicationHistory[];
  enrollment?: { student_id: string; group_code: string; order_number: string };
}

export interface Room {
  id: number;
  code: string;
  building: string;
  capacity: number;
}

export interface ScheduleEntry {
  id: number;
  offering: number;
  group_code: string;
  subject_name: string;
  subject_name_tj: string;
  subject_name_en: string;
  teacher_name: string;
  weekday: number;
  weekday_label: string;
  start_time: string;
  end_time: string;
  room: number;
  room_label: string;
  effective_from: string;
  effective_to: string;
  is_active: boolean;
}

export interface ExamResult {
  id?: number;
  sheet: number;
  student: number;
  student_name: string;
  student_code: string;
  score: string | null;
  grade_label: string;
  comment: string;
  status: string;
  version: number;
}

export interface ExamSheet {
  id: number;
  offering: number;
  group_code: string;
  subject_name: string;
  subject_name_tj: string;
  subject_name_en: string;
  teacher_name: string;
  assessment_type: string;
  exam_date: string;
  start_time: string | null;
  max_score: string;
  passing_score: string | null;
  status: string;
  version: number;
  results: ExamResult[];
}

export interface Transcript {
  student: { id: number; student_id: string; name: string; group: string };
  records: Array<{ subject_code: string; subject_name: string; subject_name_tj: string; subject_name_en: string; credits: string; assessment_type: string; score: string | null; grade_label: string; academic_year: string; semester: number }>;
  note: string;
}

export interface Subject {
  id: number;
  code: string;
  name: string;
  name_tj: string;
  name_ru: string;
  name_en: string;
  credits: string;
}

export interface TeacherSummary {
  id: number;
  user: { id: number; display_name: string; email: string };
  employee_id: string;
  position: string;
}

export interface Semester {
  id: number;
  academic_year: number;
  academic_year_name: string;
  number: number;
  start_date: string;
  end_date: string;
  status: string;
}

export interface CurriculumSubject {
  id: number;
  plan: number;
  subject: number;
  subject_name: string;
  subject_name_tj: string;
  subject_name_en: string;
  subject_code: string;
  course: number;
  semester_number: number;
  lecture_hours: number;
  practice_hours: number;
  lab_hours: number;
  independent_hours: number;
  total_hours: number;
  credits: string;
  assessment_type: string;
}

export interface CurriculumPlan {
  id: number;
  program: number;
  program_code: string;
  program_name: string;
  academic_year: number;
  academic_year_name: string;
  name: string;
  version: number;
  status: string;
  subjects: CurriculumSubject[];
}

export interface TeacherWorkload {
  id: number;
  teacher: number;
  teacher_name: string;
  curriculum_subject: number;
  subject_name: string;
  group: number;
  group_code: string;
  semester: number;
  planned_hours: number;
}
