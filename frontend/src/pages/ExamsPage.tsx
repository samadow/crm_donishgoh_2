import { CheckCheck, ClipboardPlus, FileCheck2, Save, Send, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiRequest } from "../api/client";
import { EmptyPanel, ErrorPanel, LoadingPanel } from "../components/StatePanel";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";
import { ExamSheet, Offering, Paginated, StudentSummary, Transcript } from "../types";

type ResultRow = { student: number; student_name: string; student_code: string; score: string; grade_label: string; comment: string; version: number };

export function ExamsPage() {
  const { user } = useAuth();
  const { t, language } = useI18n();
  const [sheets, setSheets] = useState<ExamSheet[]>([]);
  const [offerings, setOfferings] = useState<Offering[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [reason, setReason] = useState("");
  const [form, setForm] = useState({ offering: "", exam_date: "", max_score: "100", passing_score: "50" });

  const localizedSubject = (item: ExamSheet | Offering | Transcript["records"][number]) => language === "tj" ? item.subject_name_tj : language === "en" ? item.subject_name_en : item.subject_name;
  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true); setError("");
    try {
      if (user.role === "student") {
        setTranscript(await apiRequest<Transcript>("/transcript/"));
      } else {
        const [sheetData, offeringData] = await Promise.all([
          apiRequest<Paginated<ExamSheet>>(`/exam-sheets/?page_size=100&lang=${language}`),
          apiRequest<Paginated<Offering>>(`/offerings/?is_active=true&page_size=100&lang=${language}`),
        ]);
        setSheets(sheetData.results); setOfferings(offeringData.results);
        setSelectedId((current) => current && sheetData.results.some((sheet) => sheet.id === current) ? current : sheetData.results[0]?.id ?? null);
      }
    } catch (caught) { setError(caught instanceof Error ? caught.message : t("common.error")); }
    finally { setLoading(false); }
  }, [user, language, t]);
  useEffect(() => { void load(); }, [load]);

  const selected = sheets.find((sheet) => sheet.id === selectedId);
  useEffect(() => {
    if (!selected) { setRows([]); return; }
    const offering = offerings.find((item) => item.id === selected.offering);
    if (!offering) return;
    apiRequest<Paginated<StudentSummary>>(`/students/?group=${offering.group}&status=active&page_size=100`).then((data) => {
      const resultMap = new Map(selected.results.map((result) => [result.student, result]));
      setRows(data.results.map((student) => {
        const result = resultMap.get(student.id);
        return { student: student.id, student_name: student.user.display_name, student_code: student.student_id, score: result?.score ?? "", grade_label: result?.grade_label ?? "", comment: result?.comment ?? "", version: result?.version ?? 0 };
      }));
    }).catch((caught) => setError(caught instanceof Error ? caught.message : t("common.error")));
  }, [selected, offerings, t]);

  const createSheet = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await apiRequest("/exam-sheets/", { method: "POST", body: JSON.stringify({ ...form, offering: Number(form.offering), assessment_type: "exam" }) }); setShowCreate(false); await load(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : t("common.error")); }
    finally { setBusy(false); }
  };

  const saveResults = async () => {
    if (!selected) return; setBusy(true); setError("");
    try {
      await apiRequest(`/exam-sheets/${selected.id}/save-results/`, { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ entries: rows.map((row) => ({ student_id: row.student, score: row.score, grade_label: row.grade_label, comment: row.comment, version: row.version, reason })) }) });
      await load();
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : t("common.error")); }
    finally { setBusy(false); }
  };

  const changeSheetStatus = async (action: "submit" | "approve") => {
    if (!selected) return; setBusy(true); setError("");
    try { await apiRequest(`/exam-sheets/${selected.id}/${action}/`, { method: "POST", body: "{}" }); await load(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : t("common.error")); }
    finally { setBusy(false); }
  };

  const updateRow = (student: number, field: keyof ResultRow, value: string) => setRows((current) => current.map((row) => row.student === student ? { ...row, [field]: value } : row));
  if (!user) return null;
  if (loading) return <LoadingPanel />;
  if (error && !sheets.length && !transcript) return <ErrorPanel onRetry={load} message={error} />;

  if (user.role === "student") return (
    <div className="page">
      <header className="page-heading"><span className="eyebrow">{t("exams.eyebrow")}</span><h1>{t("exams.studentTitle")}</h1><p>{t("exams.subtitle")}</p></header>
      {transcript && <section className="transcript surface"><header><div><span>{transcript.student.student_id}</span><h2>{transcript.student.name}</h2></div><strong>{transcript.student.group}</strong></header>{transcript.records.length === 0 ? <EmptyPanel>{t("exams.empty")}</EmptyPanel> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>{t("exams.course")}</th><th>{t("exams.credits")}</th><th>{t("exams.semester")}</th><th>{t("exams.score")}</th><th>{t("exams.grade")}</th></tr></thead><tbody>{transcript.records.map((record, index) => <tr key={`${record.subject_code}-${index}`}><td><div className="table-person"><strong>{localizedSubject(record)}</strong><small>{record.subject_code} · {record.academic_year}</small></div></td><td>{record.credits}</td><td>{record.semester}</td><td><strong>{record.score ?? "—"}</strong></td><td><span className="grade-chip">{record.grade_label || "—"}</span></td></tr>)}</tbody></table></div>}</section>}
    </div>
  );

  return (
    <div className="page">
      <header className="page-heading page-heading--actions"><div><span className="eyebrow">{t("exams.eyebrow")}</span><h1>{t("exams.title")}</h1><p>{t("exams.subtitle")}</p></div><button className="button button--primary" type="button" onClick={() => setShowCreate(true)}><ClipboardPlus size={18} />{t("exams.create")}</button></header>
      {error && <div className="inline-notice inline-notice--error">{error}<button type="button" onClick={() => setError("")}><X size={15} /></button></div>}
      {sheets.length === 0 ? <EmptyPanel>{t("exams.empty")}</EmptyPanel> : <div className="exam-layout"><aside className="exam-sheets surface">{sheets.map((sheet) => <button key={sheet.id} className={selectedId === sheet.id ? "is-active" : ""} type="button" onClick={() => setSelectedId(sheet.id)}><span className={`workflow-status workflow-status--${sheet.status}`}>{t(`sheet.${sheet.status}` as "sheet.draft")}</span><strong>{localizedSubject(sheet)}</strong><small>{sheet.group_code} · {sheet.exam_date}</small></button>)}</aside>{selected && <section className="exam-editor surface"><header><div><span className="eyebrow">{selected.group_code}</span><h2>{localizedSubject(selected)}</h2></div><span className={`workflow-status workflow-status--${selected.status}`}>{t(`sheet.${selected.status}` as "sheet.draft")}</span></header><div className="data-table-wrap"><table className="data-table exam-table"><thead><tr><th>{t("journal.student")}</th><th>{t("exams.score")} / {selected.max_score}</th><th>{t("exams.grade")}</th><th>{t("exams.comment")}</th></tr></thead><tbody>{rows.map((row) => <tr key={row.student}><td><div className="table-person"><strong>{row.student_name}</strong><small>{row.student_code}</small></div></td><td><input disabled={selected.status === "approved" && !reason} inputMode="decimal" value={row.score} onChange={(event) => updateRow(row.student, "score", event.target.value)} /></td><td><input disabled={selected.status === "approved" && !reason} value={row.grade_label} onChange={(event) => updateRow(row.student, "grade_label", event.target.value)} /></td><td><input disabled={selected.status === "approved" && !reason} value={row.comment} onChange={(event) => updateRow(row.student, "comment", event.target.value)} /></td></tr>)}</tbody></table></div>{selected.status === "approved" && <label className="field exam-reason"><span>{t("journal.reason")}</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder={t("journal.reasonHint")} /></label>}<footer><button className="button button--secondary" type="button" disabled={busy} onClick={() => void saveResults()}><Save size={17} />{t("exams.save")}</button>{selected.status === "draft" && <button className="button button--primary" type="button" disabled={busy} onClick={() => void changeSheetStatus("submit")}><Send size={17} />{t("exams.submit")}</button>}{selected.status === "submitted" && user.role === "admin" && <button className="button button--primary" type="button" disabled={busy} onClick={() => void changeSheetStatus("approve")}><CheckCheck size={17} />{t("exams.approve")}</button>}</footer></section>}</div>}

      {showCreate && <div className="dialog-backdrop"><form className="dialog dialog--small surface" onSubmit={createSheet}><header><div><span className="eyebrow">{t("exams.eyebrow")}</span><h2>{t("exams.create")}</h2></div><button className="icon-button" type="button" onClick={() => setShowCreate(false)}><X /></button></header><label className="field"><span>{t("exams.course")}</span><select required value={form.offering} onChange={(event) => setForm({ ...form, offering: event.target.value })}><option value="" />{offerings.map((offering) => <option key={offering.id} value={offering.id}>{localizedSubject(offering)} · {offering.group_code}</option>)}</select></label><label className="field"><span>{t("exams.date")}</span><input type="date" required value={form.exam_date} onChange={(event) => setForm({ ...form, exam_date: event.target.value })} /></label><div className="form-grid"><label className="field"><span>{t("exams.maxScore")}</span><input inputMode="decimal" required value={form.max_score} onChange={(event) => setForm({ ...form, max_score: event.target.value })} /></label><label className="field"><span>{t("exams.passScore")}</span><input inputMode="decimal" value={form.passing_score} onChange={(event) => setForm({ ...form, passing_score: event.target.value })} /></label></div><footer><button className="button button--secondary" type="button" onClick={() => setShowCreate(false)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy} type="submit"><FileCheck2 size={18} />{t("exams.create")}</button></footer></form></div>}
    </div>
  );
}

