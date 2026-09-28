import { BookCopy, CheckCircle2, Clock3, Plus, UserRoundCog, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiRequest } from "../../api/client";
import { EmptyPanel, ErrorPanel, LoadingPanel } from "../../components/StatePanel";
import { useI18n } from "../../context/I18nContext";
import { AcademicYear, CurriculumPlan, Group, Paginated, Program, Semester, Subject, TeacherSummary, TeacherWorkload } from "../../types";

type View = "plans" | "workload";

export function PlanningPage() {
  const { t, language } = useI18n();
  const [view, setView] = useState<View>("plans");
  const [plans, setPlans] = useState<CurriculumPlan[]>([]);
  const [workloads, setWorkloads] = useState<TeacherWorkload[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<TeacherSummary[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [semesters, setSemesters] = useState<Semester[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [dialog, setDialog] = useState<"plan" | "subject" | "workload" | null>(null);
  const [planForm, setPlanForm] = useState({ program: "", academic_year: "", name: "", version: "1" });
  const [subjectForm, setSubjectForm] = useState({ subject: "", course: "1", semester_number: "1", lecture_hours: "24", practice_hours: "24", lab_hours: "0", independent_hours: "72", credits: "5", assessment_type: "exam" });
  const [workloadForm, setWorkloadForm] = useState({ teacher: "", curriculum_subject: "", group: "", semester: "", planned_hours: "48" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [planData, workloadData, programData, yearData, subjectData, teacherData, groupData, semesterData] = await Promise.all([
        apiRequest<Paginated<CurriculumPlan>>("/curriculum-plans/?page_size=100"),
        apiRequest<Paginated<TeacherWorkload>>("/teacher-workloads/?page_size=100"),
        apiRequest<Paginated<Program>>(`/programs/?page_size=100&lang=${language}`),
        apiRequest<Paginated<AcademicYear>>("/academic-years/?page_size=100"),
        apiRequest<Paginated<Subject>>(`/subjects/?page_size=100&lang=${language}`),
        apiRequest<Paginated<TeacherSummary>>("/teachers/?page_size=100"),
        apiRequest<Paginated<Group>>("/groups/?is_active=true&page_size=100"),
        apiRequest<Paginated<Semester>>("/semesters/?page_size=100"),
      ]);
      setPlans(planData.results); setWorkloads(workloadData.results); setPrograms(programData.results); setYears(yearData.results);
      setSubjects(subjectData.results); setTeachers(teacherData.results); setGroups(groupData.results); setSemesters(semesterData.results);
      setSelectedPlanId((current) => current && planData.results.some((item) => item.id === current) ? current : planData.results[0]?.id ?? null);
    } catch (caught) { setError(caught instanceof Error ? caught.message : t("common.error")); }
    finally { setLoading(false); }
  }, [language, t]);
  useEffect(() => { void load(); }, [load]);

  const selectedPlan = plans.find((item) => item.id === selectedPlanId) || null;
  const curriculumEntries = useMemo(() => plans.flatMap((plan) => plan.subjects.map((entry) => ({ ...entry, planName: plan.name }))), [plans]);
  const localProgram = (item: Program) => language === "tj" ? item.name_tj : language === "en" ? item.name_en : item.name_ru;
  const localSubject = (item: Subject) => language === "tj" ? item.name_tj : language === "en" ? item.name_en : item.name_ru;
  const planHours = selectedPlan?.subjects.reduce((total, entry) => total + entry.total_hours, 0) || 0;

  const savePlan = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const created = await apiRequest<CurriculumPlan>("/curriculum-plans/", { method: "POST", body: JSON.stringify({ ...planForm, program: Number(planForm.program), academic_year: Number(planForm.academic_year), version: Number(planForm.version), status: "draft" }) });
      setDialog(null); setPlanForm({ program: "", academic_year: "", name: "", version: "1" }); setNotice(t("planning.saved")); await load(); setSelectedPlanId(created.id);
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : t("common.error")); }
    finally { setBusy(false); }
  };
  const saveSubject = async (event: FormEvent) => {
    event.preventDefault(); if (!selectedPlan) return; setBusy(true); setError("");
    const numericFields = ["course", "semester_number", "lecture_hours", "practice_hours", "lab_hours", "independent_hours"] as const;
    const payload: Record<string, string | number> = { ...subjectForm, plan: selectedPlan.id, subject: Number(subjectForm.subject) };
    numericFields.forEach((field) => { payload[field] = Number(subjectForm[field]); });
    try { await apiRequest("/curriculum-subjects/", { method: "POST", body: JSON.stringify(payload) }); setDialog(null); setNotice(t("planning.saved")); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : t("common.error")); } finally { setBusy(false); }
  };
  const saveWorkload = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await apiRequest("/teacher-workloads/", { method: "POST", body: JSON.stringify({ teacher: Number(workloadForm.teacher), curriculum_subject: Number(workloadForm.curriculum_subject), group: Number(workloadForm.group), semester: Number(workloadForm.semester), planned_hours: Number(workloadForm.planned_hours) }) }); setDialog(null); setNotice(t("planning.saved")); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : t("common.error")); } finally { setBusy(false); }
  };
  const activatePlan = async () => {
    if (!selectedPlan) return; setBusy(true); setError("");
    try { await apiRequest(`/curriculum-plans/${selectedPlan.id}/`, { method: "PATCH", body: JSON.stringify({ status: "active" }) }); setNotice(t("planning.activated")); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : t("common.error")); } finally { setBusy(false); }
  };

  if (loading && !plans.length) return <LoadingPanel />;
  if (error && !programs.length) return <ErrorPanel onRetry={load} message={error} />;
  return <div className="page">
    <header className="page-heading page-heading--actions"><div><span className="eyebrow">{t("planning.eyebrow")}</span><h1>{t("planning.title")}</h1><p>{t("planning.subtitle")}</p></div><div className="page-heading__actions"><button className="button button--secondary" type="button" onClick={() => setDialog("workload")}><UserRoundCog size={18} />{t("planning.assign")}</button><button className="button button--primary" type="button" onClick={() => setDialog("plan")}><Plus size={18} />{t("planning.newPlan")}</button></div></header>
    {(error || notice) && <div className={`inline-notice ${error ? "inline-notice--error" : "inline-notice--success"}`}>{error || notice}<button type="button" onClick={() => { setError(""); setNotice(""); }}><X size={15} /></button></div>}
    <nav className="module-tabs" aria-label={t("planning.title")}><button type="button" className={view === "plans" ? "is-active" : ""} onClick={() => setView("plans")}><BookCopy size={16} />{t("planning.plans")}</button><button type="button" className={view === "workload" ? "is-active" : ""} onClick={() => setView("workload")}><UserRoundCog size={16} />{t("planning.workload")}</button></nav>

    {view === "plans" && (plans.length ? <section className="planning-layout"><aside className="surface plan-list">{plans.map((plan) => <button type="button" className={plan.id === selectedPlanId ? "is-active" : ""} key={plan.id} onClick={() => setSelectedPlanId(plan.id)}><span className={`workflow-status workflow-status--${plan.status}`}>{t(`plan.${plan.status}` as "plan.draft")}</span><strong>{plan.name}</strong><small>{plan.program_code} · {plan.academic_year_name} · v{plan.version}</small></button>)}</aside>{selectedPlan && <article className="surface plan-editor"><header><div><span className="eyebrow">{selectedPlan.program_code} · {selectedPlan.academic_year_name}</span><h2>{selectedPlan.name}</h2></div><div><span className="plan-hours"><Clock3 />{planHours} {t("planning.hours")}</span>{selectedPlan.status === "draft" && <button className="button button--secondary button--small" disabled={busy || !selectedPlan.subjects.length} type="button" onClick={() => void activatePlan()}><CheckCircle2 size={15} />{t("planning.activate")}</button>}<button className="button button--primary button--small" type="button" onClick={() => setDialog("subject")}><Plus size={15} />{t("planning.addSubject")}</button></div></header>{selectedPlan.subjects.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr><th>{t("planning.subject")}</th><th>{t("planning.course")}</th><th>{t("planning.semester")}</th><th>{t("planning.classHours")}</th><th>{t("planning.independent")}</th><th>{t("planning.credits")}</th><th>{t("planning.control")}</th></tr></thead><tbody>{selectedPlan.subjects.map((entry) => <tr key={entry.id}><td><strong>{entry.subject_code}</strong><br /><small>{language === "tj" ? entry.subject_name_tj : language === "en" ? entry.subject_name_en : entry.subject_name}</small></td><td>{entry.course}</td><td>{entry.semester_number}</td><td>{entry.lecture_hours + entry.practice_hours + entry.lab_hours}</td><td>{entry.independent_hours}</td><td>{entry.credits}</td><td><span className="workflow-status">{t(`assessment.${entry.assessment_type}` as "assessment.exam")}</span></td></tr>)}</tbody></table></div> : <EmptyPanel>{t("planning.emptySubjects")}</EmptyPanel>}</article>}</section> : <EmptyPanel>{t("planning.emptyPlans")}</EmptyPanel>)}

    {view === "workload" && <section className="surface module-table-wrap">{workloads.length ? <table className="data-table module-table"><thead><tr><th>{t("planning.teacher")}</th><th>{t("planning.subject")}</th><th>{t("admissions.group")}</th><th>{t("planning.semester")}</th><th>{t("planning.hours")}</th></tr></thead><tbody>{workloads.map((item) => <tr key={item.id}><td><strong>{item.teacher_name}</strong></td><td>{item.subject_name}</td><td>{item.group_code}</td><td>{semesters.find((semester) => semester.id === item.semester)?.academic_year_name} · {semesters.find((semester) => semester.id === item.semester)?.number}</td><td><span className="grade-chip">{item.planned_hours}</span></td></tr>)}</tbody></table> : <EmptyPanel>{t("planning.emptyWorkload")}</EmptyPanel>}</section>}

    {dialog === "plan" && <div className="dialog-backdrop"><form className="dialog dialog--small surface" onSubmit={savePlan}><header><h2>{t("planning.newPlan")}</h2><button className="icon-button" type="button" onClick={() => setDialog(null)}><X /></button></header><label className="field"><span>{t("admissions.program")}</span><select required value={planForm.program} onChange={(event) => setPlanForm({ ...planForm, program: event.target.value })}><option value="" />{programs.map((item) => <option key={item.id} value={item.id}>{item.code} · {localProgram(item)}</option>)}</select></label><label className="field"><span>{t("admissions.year")}</span><select required value={planForm.academic_year} onChange={(event) => setPlanForm({ ...planForm, academic_year: event.target.value })}><option value="" />{years.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="field"><span>{t("planning.name")}</span><input required value={planForm.name} onChange={(event) => setPlanForm({ ...planForm, name: event.target.value })} /></label><label className="field"><span>{t("planning.version")}</span><input type="number" min="1" required value={planForm.version} onChange={(event) => setPlanForm({ ...planForm, version: event.target.value })} /></label><footer><button className="button button--secondary" type="button" onClick={() => setDialog(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy}>{t("journal.save")}</button></footer></form></div>}
    {dialog === "subject" && selectedPlan && <div className="dialog-backdrop"><form className="dialog surface" onSubmit={saveSubject}><header><div><span className="eyebrow">{selectedPlan.name}</span><h2>{t("planning.addSubject")}</h2></div><button className="icon-button" type="button" onClick={() => setDialog(null)}><X /></button></header><div className="form-grid"><label className="field form-grid__wide"><span>{t("planning.subject")}</span><select required value={subjectForm.subject} onChange={(event) => setSubjectForm({ ...subjectForm, subject: event.target.value })}><option value="" />{subjects.map((item) => <option key={item.id} value={item.id}>{item.code} · {localSubject(item)}</option>)}</select></label>{(["course", "semester_number", "lecture_hours", "practice_hours", "lab_hours", "independent_hours", "credits"] as const).map((field) => <label className="field" key={field}><span>{t((({ course: "planning.course", semester_number: "planning.semester", lecture_hours: "planning.lectures", practice_hours: "planning.practice", lab_hours: "planning.labs", independent_hours: "planning.independent", credits: "planning.credits" }) as const)[field])}</span><input type="number" min="0" step={field === "credits" ? ".5" : "1"} required value={subjectForm[field]} onChange={(event) => setSubjectForm({ ...subjectForm, [field]: event.target.value })} /></label>)}<label className="field"><span>{t("planning.control")}</span><select value={subjectForm.assessment_type} onChange={(event) => setSubjectForm({ ...subjectForm, assessment_type: event.target.value })}><option value="exam">{t("assessment.exam")}</option><option value="credit">{t("assessment.credit")}</option><option value="differentiated_credit">{t("assessment.differentiated_credit")}</option></select></label></div><footer><button className="button button--secondary" type="button" onClick={() => setDialog(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy}>{t("journal.save")}</button></footer></form></div>}
    {dialog === "workload" && <div className="dialog-backdrop"><form className="dialog dialog--small surface" onSubmit={saveWorkload}><header><h2>{t("planning.assign")}</h2><button className="icon-button" type="button" onClick={() => setDialog(null)}><X /></button></header><label className="field"><span>{t("planning.teacher")}</span><select required value={workloadForm.teacher} onChange={(event) => setWorkloadForm({ ...workloadForm, teacher: event.target.value })}><option value="" />{teachers.map((item) => <option key={item.id} value={item.id}>{item.user.display_name} · {item.employee_id}</option>)}</select></label><label className="field"><span>{t("planning.subject")}</span><select required value={workloadForm.curriculum_subject} onChange={(event) => setWorkloadForm({ ...workloadForm, curriculum_subject: event.target.value })}><option value="" />{curriculumEntries.map((item) => <option key={item.id} value={item.id}>{item.subject_code} · {item.planName}</option>)}</select></label><label className="field"><span>{t("admissions.group")}</span><select required value={workloadForm.group} onChange={(event) => setWorkloadForm({ ...workloadForm, group: event.target.value })}><option value="" />{groups.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}</select></label><label className="field"><span>{t("planning.semester")}</span><select required value={workloadForm.semester} onChange={(event) => setWorkloadForm({ ...workloadForm, semester: event.target.value })}><option value="" />{semesters.map((item) => <option key={item.id} value={item.id}>{item.academic_year_name} · {item.number}</option>)}</select></label><label className="field"><span>{t("planning.hours")}</span><input type="number" min="1" required value={workloadForm.planned_hours} onChange={(event) => setWorkloadForm({ ...workloadForm, planned_hours: event.target.value })} /></label><footer><button className="button button--secondary" type="button" onClick={() => setDialog(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy}>{t("journal.save")}</button></footer></form></div>}
  </div>;
}
