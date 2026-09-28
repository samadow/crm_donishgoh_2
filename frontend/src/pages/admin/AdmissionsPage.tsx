import { AlertCircle, ArrowRight, CheckCircle2, FilePlus2, FileSpreadsheet, Search, UserPlus, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiRequest } from "../../api/client";
import { EmptyPanel, ErrorPanel, LoadingPanel } from "../../components/StatePanel";
import { useI18n } from "../../context/I18nContext";
import { AcademicYear, AdmissionApplication, Group, Paginated, Program } from "../../types";

const nextStatus: Record<string, string | undefined> = {
  draft: "submitted",
  submitted: "under_review",
  under_review: "documents_verified",
  documents_verified: "accepted",
  rejected: "under_review",
};

const emptyIntake = {
  first_name: "", last_name: "", middle_name: "", birth_date: "", email: "", phone: "", national_id: "",
  program: "", academic_year: "", application_number: "",
};
type ImportIssue = { field: string; code: string; message: string };
type ImportRow = { row: number; data: Record<string, string>; errors: ImportIssue[] };
type ImportBatch = { id: number; file_name: string; rows: ImportRow[]; row_count: number; valid_count: number; error_count: number; status: "preview" | "committed" };

export function AdmissionsPage() {
  const { t, language } = useI18n();
  const [applications, setApplications] = useState<AdmissionApplication[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [intake, setIntake] = useState(emptyIntake);
  const [enrolling, setEnrolling] = useState<AdmissionApplication | null>(null);
  const [enrollment, setEnrollment] = useState({ group: "", order_number: "", temporary_password: "" });
  const [busy, setBusy] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importBatch, setImportBatch] = useState<ImportBatch | null>(null);
  const importIssue = (issue: ImportIssue) => t(issue.code === "duplicate" ? "admissions.issueDuplicate" : issue.code === "unknown" ? "admissions.issueUnknown" : issue.code === "invalid" ? "admissions.issueInvalid" : "admissions.issueRequired");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [appData, programData, yearData, groupData] = await Promise.all([
        apiRequest<Paginated<AdmissionApplication>>(`/applications/?page_size=100&lang=${language}`),
        apiRequest<Paginated<Program>>(`/programs/?page_size=100&lang=${language}`),
        apiRequest<Paginated<AcademicYear>>( `/academic-years/?page_size=100`),
        apiRequest<Paginated<Group>>(`/groups/?is_active=true&page_size=100`),
      ]);
      setApplications(appData.results); setPrograms(programData.results); setYears(yearData.results); setGroups(groupData.results);
    } catch (caught) { setError(caught instanceof Error ? caught.message : t("admissions.error")); }
    finally { setLoading(false); }
  }, [language, t]);

  useEffect(() => { void load(); }, [load]);
  const localProgram = (item: AdmissionApplication | Program) => {
    if ("program_name_tj" in item) return language === "tj" ? item.program_name_tj : language === "en" ? item.program_name_en : item.program_name;
    return language === "tj" ? item.name_tj : language === "en" ? item.name_en : item.name_ru;
  };
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return query ? applications.filter((item) => `${item.application_number} ${item.applicant_detail.display_name} ${item.applicant_detail.email}`.toLocaleLowerCase().includes(query)) : applications;
  }, [applications, search]);

  const createApplication = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await apiRequest("/applications/intake/", { method: "POST", body: JSON.stringify({
        applicant: { first_name: intake.first_name, last_name: intake.last_name, middle_name: intake.middle_name, birth_date: intake.birth_date, email: intake.email, phone: intake.phone, national_id: intake.national_id },
        program: Number(intake.program), academic_year: Number(intake.academic_year), application_number: intake.application_number, source: "office",
      }) });
      setIntake(emptyIntake); setShowCreate(false); setNotice(t("admissions.success")); await load();
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : t("admissions.error")); }
    finally { setBusy(false); }
  };

  const advance = async (application: AdmissionApplication) => {
    const status = nextStatus[application.status];
    if (!status) return;
    setBusy(true); setError("");
    try { await apiRequest(`/applications/${application.id}/transition/`, { method: "POST", body: JSON.stringify({ status, reason: "Workflow review completed" }) }); setNotice(t("admissions.success")); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : t("admissions.error")); }
    finally { setBusy(false); }
  };

  const enrol = async (event: FormEvent) => {
    event.preventDefault(); if (!enrolling) return;
    setBusy(true); setError("");
    try {
      await apiRequest(`/applications/${enrolling.id}/enroll/`, { method: "POST", body: JSON.stringify({ group: Number(enrollment.group), order_number: enrollment.order_number, temporary_password: enrollment.temporary_password }) });
      setEnrolling(null); setEnrollment({ group: "", order_number: "", temporary_password: "" }); setNotice(t("admissions.success")); await load();
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : t("admissions.error")); }
    finally { setBusy(false); }
  };

  const previewImport = async (event: FormEvent) => {
    event.preventDefault(); if (!importFile) return;
    setBusy(true); setError(""); setImportBatch(null);
    const body = new FormData(); body.append("file", importFile);
    try { setImportBatch(await apiRequest<ImportBatch>("/admission-imports/preview/", { method: "POST", body })); }
    catch { setError(t("admissions.importError")); }
    finally { setBusy(false); }
  };

  const commitImport = async () => {
    if (!importBatch || importBatch.error_count) return;
    setBusy(true); setError("");
    try {
      await apiRequest(`/admission-imports/${importBatch.id}/commit/`, { method: "POST", body: JSON.stringify({}) });
      setNotice(t("admissions.imported")); setShowImport(false); setImportFile(null); setImportBatch(null); await load();
    } catch { setError(t("admissions.importError")); }
    finally { setBusy(false); }
  };

  if (loading && !applications.length) return <LoadingPanel />;
  if (error && !applications.length) return <ErrorPanel onRetry={load} message={error} />;
  return (
    <div className="page">
      <header className="page-heading page-heading--actions"><div><span className="eyebrow">{t("admissions.eyebrow")}</span><h1>{t("admissions.title")}</h1><p>{t("admissions.subtitle")}</p></div><div className="page-heading__actions"><button className="button button--secondary" type="button" onClick={() => setShowImport(true)}><FileSpreadsheet size={18} />{t("admissions.import")}</button><button className="button button--primary" type="button" onClick={() => setShowCreate(true)}><UserPlus size={18} />{t("admissions.new")}</button></div></header>
      {(error || notice) && <div className={`inline-notice ${error ? "inline-notice--error" : "inline-notice--success"}`}>{error || notice}<button type="button" onClick={() => { setError(""); setNotice(""); }}><X size={15} /></button></div>}
      <section className="surface module-toolbar"><label className="search-field"><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("admissions.search")} /></label><span className="count-pill">{filtered.length}</span></section>
      <section className="surface module-table-wrap">
        {filtered.length === 0 ? <EmptyPanel>{t("admissions.empty")}</EmptyPanel> : <table className="data-table module-table"><thead><tr><th>{t("admissions.number")}</th><th>{t("admissions.applicant")}</th><th>{t("admissions.program")}</th><th>{t("admissions.year")}</th><th>{t("admissions.status")}</th><th /></tr></thead><tbody>{filtered.map((application) => <tr key={application.id}><td><strong>{application.application_number}</strong></td><td><div className="table-person"><strong>{application.applicant_detail.display_name}</strong><small>{application.applicant_detail.email}</small></div></td><td>{localProgram(application)}</td><td>{application.academic_year_name}</td><td><span className={`workflow-status workflow-status--${application.status}`}>{t(`application.${application.status}` as "application.draft")}</span></td><td><div className="table-actions">{nextStatus[application.status] && <button className="button button--secondary button--small" type="button" disabled={busy} onClick={() => void advance(application)}>{t("admissions.next")}<ArrowRight size={15} /></button>}{application.status === "accepted" && <button className="button button--primary button--small" type="button" onClick={() => setEnrolling(application)}><CheckCircle2 size={15} />{t("admissions.enroll")}</button>}</div></td></tr>)}</tbody></table>}
      </section>

      {showCreate && <div className="dialog-backdrop" role="presentation"><form className="dialog surface" onSubmit={createApplication}><header><div><span className="eyebrow">{t("admissions.eyebrow")}</span><h2>{t("admissions.createTitle")}</h2></div><button className="icon-button" type="button" onClick={() => setShowCreate(false)}><X /></button></header><div className="form-grid">{(["last_name", "first_name", "middle_name", "birth_date", "email", "phone", "national_id", "application_number"] as const).map((field) => <label className="field" key={field}><span>{t(({ last_name: "admissions.lastName", first_name: "admissions.firstName", middle_name: "admissions.middleName", birth_date: "admissions.birthDate", email: "admissions.email", phone: "admissions.phone", national_id: "admissions.nationalId", application_number: "admissions.applicationNumber" } as const)[field])}</span><input type={field === "birth_date" ? "date" : field === "email" ? "email" : "text"} required={field !== "middle_name" && field !== "national_id"} value={intake[field]} onChange={(event) => setIntake({ ...intake, [field]: event.target.value })} /></label>)}<label className="field"><span>{t("admissions.program")}</span><select required value={intake.program} onChange={(event) => setIntake({ ...intake, program: event.target.value })}><option value="" />{programs.map((program) => <option key={program.id} value={program.id}>{program.code} · {localProgram(program)}</option>)}</select></label><label className="field"><span>{t("admissions.year")}</span><select required value={intake.academic_year} onChange={(event) => setIntake({ ...intake, academic_year: event.target.value })}><option value="" />{years.map((year) => <option key={year.id} value={year.id}>{year.name}</option>)}</select></label></div><footer><button className="button button--secondary" type="button" onClick={() => setShowCreate(false)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy} type="submit"><FilePlus2 size={18} />{t("admissions.save")}</button></footer></form></div>}

      {enrolling && <div className="dialog-backdrop" role="presentation"><form className="dialog dialog--small surface" onSubmit={enrol}><header><div><span className="eyebrow">{enrolling.application_number}</span><h2>{t("admissions.enrollTitle")}</h2></div><button className="icon-button" type="button" onClick={() => setEnrolling(null)}><X /></button></header><label className="field"><span>{t("admissions.group")}</span><select required value={enrollment.group} onChange={(event) => setEnrollment({ ...enrollment, group: event.target.value })}><option value="" />{groups.filter((group) => group.program === enrolling.program).map((group) => <option key={group.id} value={group.id}>{group.code}</option>)}</select></label><label className="field"><span>{t("admissions.order")}</span><input required value={enrollment.order_number} onChange={(event) => setEnrollment({ ...enrollment, order_number: event.target.value })} /></label><label className="field"><span>{t("admissions.password")}</span><input required minLength={12} type="password" value={enrollment.temporary_password} onChange={(event) => setEnrollment({ ...enrollment, temporary_password: event.target.value })} /></label><footer><button className="button button--secondary" type="button" onClick={() => setEnrolling(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy} type="submit">{t("admissions.enroll")}</button></footer></form></div>}

      {showImport && <div className="dialog-backdrop" role="presentation"><div className="dialog import-dialog surface"><header><div><span className="eyebrow">{t("admissions.eyebrow")}</span><h2>{t("admissions.importTitle")}</h2></div><button className="icon-button" type="button" onClick={() => { setShowImport(false); setImportBatch(null); }}><X /></button></header><p className="import-hint">{t("admissions.importHint")}</p><code className="import-columns">application_number · first_name · last_name · birth_date · email · phone · national_id · program_code · academic_year</code><form className="import-picker" onSubmit={previewImport}><label><FileSpreadsheet size={22} /><span>{importFile?.name || t("admissions.selectFile")}</span><input type="file" accept=".xlsx,.csv" required onChange={(event) => { setImportFile(event.target.files?.[0] || null); setImportBatch(null); }} /></label><button className="button button--secondary" disabled={busy || !importFile}>{t("admissions.preview")}</button></form>{importBatch && <><div className={`import-summary ${importBatch.error_count ? "import-summary--error" : "import-summary--ready"}`}><span><CheckCircle2 />{t("admissions.valid")}: <strong>{importBatch.valid_count}</strong></span><span><AlertCircle />{t("admissions.errors")}: <strong>{importBatch.error_count}</strong></span><small>{importBatch.error_count ? t("admissions.importBlocked") : t("admissions.importReady")}</small></div><div className="import-preview"><table className="data-table"><thead><tr><th>#</th><th>{t("admissions.number")}</th><th>{t("admissions.applicant")}</th><th>{t("admissions.program")}</th><th>{t("admissions.status")}</th></tr></thead><tbody>{importBatch.rows.map((item) => <tr key={item.row} className={item.errors.length ? "has-error" : ""}><td>{item.row}</td><td>{item.data.application_number}</td><td><strong>{item.data.last_name} {item.data.first_name}</strong><small>{item.data.email}</small></td><td>{item.data.program_code}</td><td>{item.errors.length ? <span className="import-errors">{item.errors.map(importIssue).join(" ")}</span> : <span className="workflow-status workflow-status--accepted">{t("admissions.valid")}</span>}</td></tr>)}</tbody></table></div></>}<footer><button className="button button--secondary" type="button" onClick={() => { setShowImport(false); setImportBatch(null); }}>{t("admissions.cancel")}</button><button className="button button--primary" type="button" disabled={busy || !importBatch || importBatch.error_count > 0} onClick={() => void commitImport()}>{t("admissions.commitImport")}</button></footer></div></div>}
    </div>
  );
}
