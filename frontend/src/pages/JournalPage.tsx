import { BarChart3, Check, CheckCheck, Clock3, History, RefreshCw, Search, ShieldAlert, UserCheck, WifiOff, XCircle } from "lucide-react";
import { KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, apiRequest } from "../api/client";
import { EmptyPanel, ErrorPanel, LoadingPanel } from "../components/StatePanel";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";
import { AttendanceRecord, AttendanceStatus, ClassSession, Offering, Paginated, StudentSummary } from "../types";

type SaveState = "saved" | "unsaved" | "saving" | "error" | "conflict" | "pending";
type JournalRow = AttendanceRecord & { student_detail: StudentSummary };
type ReportPeriod = "day" | "week" | "month" | "semester";
type ReportRow = { student_id: number; student__student_id: string; student__user__first_name: string; student__user__last_name: string; entries: number; present_hours: number; absent_hours: number; late_hours: number; excused_hours: number; average_grade: string | null };
type AttendanceReport = { period: ReportPeriod; start: string; end: string; overall: Omit<ReportRow, "student_id" | "student__student_id" | "student__user__first_name" | "student__user__last_name">; students: ReportRow[] };
type PendingChange = { id: number; student_name: string; student_code: string; subject_name: string; group_code: string; session_date: string; old_value: Record<string, unknown>; new_value: Record<string, unknown>; reason: string; author_name: string; created_at: string };

const statusOrder: AttendanceStatus[] = ["present", "absent", "late", "excused"];

function makeRow(student: StudentSummary, sessionId: number, existing?: AttendanceRecord): JournalRow {
  return existing ? { ...existing, student_detail: student } : {
    session: sessionId,
    student: student.id,
    student_detail: student,
    status: "unmarked",
    grade: null,
    grade_type: "daily",
    comment: "",
    is_confirmed: false,
    version: 0,
  };
}

function StatusControl({ value, onChange, readOnly = false }: { value: AttendanceStatus; onChange?: (value: AttendanceStatus) => void; readOnly?: boolean }) {
  const { t } = useI18n();
  if (readOnly) return <span className={`status-badge status-badge--${value}`}>{t(`status.${value}` as "status.present")}</span>;
  return (
    <div className="status-control" role="group" aria-label={t("journal.attendance")}>
      {statusOrder.map((status) => (
        <button key={status} type="button" className={value === status ? "is-active" : ""} data-status={status} onClick={() => onChange?.(status)} aria-pressed={value === status} title={t(`status.${status}` as "status.present")}>
          <span aria-hidden="true">{t(`status.${status}` as "status.present").slice(0, 1).toLocaleUpperCase()}</span>
          <span className="status-control__label">{t(`status.${status}` as "status.present")}</span>
        </button>
      ))}
    </div>
  );
}

function SaveIndicator({ state }: { state: SaveState }) {
  const { t } = useI18n();
  const map = {
    saved: { icon: CheckCheck, text: t("journal.saved") },
    unsaved: { icon: Clock3, text: t("journal.unsaved") },
    saving: { icon: RefreshCw, text: t("journal.saving") },
    error: { icon: WifiOff, text: t("journal.saveError") },
    conflict: { icon: ShieldAlert, text: t("journal.conflict") },
    pending: { icon: Clock3, text: t("journal.pending") },
  } as const;
  const current = map[state];
  const Icon = current.icon;
  return <div className={`save-indicator save-indicator--${state}`} role="status"><Icon className={state === "saving" ? "spin" : ""} size={16} />{current.text}</div>;
}

export function JournalPage() {
  const { user } = useAuth();
  const { t, language } = useI18n();
  const readOnly = user?.role === "student";
  const [offerings, setOfferings] = useState<Offering[]>([]);
  const [offeringId, setOfferingId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<ClassSession[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [rows, setRows] = useState<JournalRow[]>([]);
  const [search, setSearch] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [error, setError] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [showReport, setShowReport] = useState(false);
  const [reportPeriod, setReportPeriod] = useState<ReportPeriod>("month");
  const [report, setReport] = useState<AttendanceReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [showApprovals, setShowApprovals] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<PendingChange[]>([]);
  const rowsRef = useRef<JournalRow[]>([]);
  const dirtyRef = useRef<Set<number>>(new Set());
  const saveTimerRef = useRef<number | null>(null);
  const requestKeyRef = useRef<string | null>(null);
  const reasonRef = useRef("");

  useEffect(() => { rowsRef.current = rows; }, [rows]);
  useEffect(() => { reasonRef.current = reason; }, [reason]);

  const loadOfferings = useCallback(async () => {
    setLoading(true); setError(false);
    try {
      const data = await apiRequest<Paginated<Offering>>(`/offerings/?is_active=true&lang=${language}`);
      setOfferings(data.results);
      setOfferingId((current) => current && data.results.some((item) => item.id === current) ? current : data.results[0]?.id ?? null);
    } catch { setError(true); } finally { setLoading(false); }
  }, [language]);

  useEffect(() => { void loadOfferings(); }, [loadOfferings]);

  useEffect(() => {
    if (!offeringId) { setSessions([]); setSessionId(null); return; }
    setTableLoading(true);
    apiRequest<Paginated<ClassSession>>(`/sessions/?offering=${offeringId}&ordering=-date,-start_time&lang=${language}`)
      .then((data) => {
        setSessions(data.results);
        const today = new Date().toISOString().slice(0, 10);
        setSessionId((current) => current && data.results.some((item) => item.id === current) ? current : data.results.find((item) => item.date === today)?.id ?? data.results[0]?.id ?? null);
      })
      .catch(() => setError(true))
      .finally(() => setTableLoading(false));
  }, [offeringId, language]);

  const loadRows = useCallback(async () => {
    if (!sessionId || !offeringId) { setRows([]); return; }
    const offering = offerings.find((item) => item.id === offeringId);
    if (!offering) return;
    setTableLoading(true);
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    dirtyRef.current.clear(); requestKeyRef.current = null;
    try {
      const [studentData, records] = await Promise.all([
        apiRequest<Paginated<StudentSummary>>(`/students/?group=${offering.group}&status=active&page_size=100`),
        apiRequest<AttendanceRecord[]>(`/sessions/${sessionId}/records/`),
      ]);
      const recordMap = new Map(records.map((record) => [record.student, record]));
      const nextRows = studentData.results.map((student) => makeRow(student, sessionId, recordMap.get(student.id)));
      setRows(nextRows); rowsRef.current = nextRows; setSaveState("saved"); setReason("");
    } catch { setError(true); } finally { setTableLoading(false); }
  }, [sessionId, offeringId, offerings]);

  useEffect(() => { void loadRows(); }, [loadRows]);

  const saveChanges = useCallback(async (confirm = false) => {
    if (readOnly || !sessionId || dirtyRef.current.size === 0) return;
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    const dirtyIds = [...dirtyRef.current];
    const dirtyRows = rowsRef.current.filter((row) => dirtyRef.current.has(row.student));
    const nextKey = requestKeyRef.current || crypto.randomUUID();
    requestKeyRef.current = nextKey;
    setSaveState("saving");
    try {
      const result = await apiRequest<{ records: Array<Partial<JournalRow> & { student_id: number; pending: boolean }>; pending_approval: number }>(`/sessions/${sessionId}/bulk-mark/`, {
        method: "POST",
        headers: { "Idempotency-Key": nextKey },
        body: JSON.stringify({ entries: dirtyRows.map((row) => ({
          student_id: row.student,
          status: row.status,
          grade: row.grade,
          grade_type: row.grade_type,
          comment: row.comment,
          is_confirmed: confirm || row.is_confirmed,
          version: row.version,
          reason: reasonRef.current,
        })) }),
      });
      const updateMap = new Map(result.records.map((record) => [record.student_id, record]));
      setRows((current) => current.map((row) => {
        const update = updateMap.get(row.student);
        return update ? { ...row, ...update, student: row.student, student_detail: row.student_detail } : row;
      }));
      dirtyIds.forEach((id) => dirtyRef.current.delete(id));
      requestKeyRef.current = null;
      setSaveState(result.pending_approval ? "pending" : "saved");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        setSaveState("conflict");
        await loadRows();
      } else {
        setSaveState("error");
      }
    }
  }, [readOnly, sessionId, loadRows]);

  const scheduleSave = useCallback(() => {
    setSaveState("unsaved");
    requestKeyRef.current = null;
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    saveTimerRef.current = window.setTimeout(() => void saveChanges(false), 900);
  }, [saveChanges]);

  const updateRow = <K extends keyof JournalRow>(studentId: number, field: K, value: JournalRow[K]) => {
    if (readOnly) return;
    setRows((current) => {
      const next = current.map((row) => row.student === studentId ? { ...row, [field]: value } : row);
      rowsRef.current = next;
      return next;
    });
    dirtyRef.current.add(studentId);
    scheduleSave();
  };

  const markAllPresent = () => {
    const visibleIds = new Set(filteredRows.map((row) => row.student));
    const next = rowsRef.current.map((row) => visibleIds.has(row.student) ? { ...row, status: "present" as AttendanceStatus } : row);
    setRows(next); rowsRef.current = next;
    visibleIds.forEach((id) => dirtyRef.current.add(id));
    scheduleSave();
  };

  const confirmEntries = () => {
    const next = rowsRef.current.map((row) => ({ ...row, is_confirmed: true }));
    next.forEach((row) => { if (!rowsRef.current.find((current) => current.student === row.student)?.is_confirmed) dirtyRef.current.add(row.student); });
    rowsRef.current = next;
    setRows(next);
    void saveChanges(true);
  };

  const gradeKeyDown = (event: KeyboardEvent<HTMLInputElement>, index: number) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const next = index + (event.key === "ArrowDown" ? 1 : -1);
    document.querySelector<HTMLInputElement>(`[data-grade-index="${next}"]`)?.focus();
  };

  const filteredRows = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    if (!query) return rows;
    return rows.filter((row) => `${row.student_detail.user.display_name} ${row.student_detail.student_id}`.toLocaleLowerCase().includes(query));
  }, [rows, search]);
  const selectedSession = sessions.find((item) => item.id === sessionId);
  const localizedOffering = (item: Offering) => language === "tj" ? item.subject_name_tj : language === "en" ? item.subject_name_en : item.subject_name;
  const localizedStatus = (value: unknown) => typeof value === "string" && (["unmarked", ...statusOrder] as string[]).includes(value) ? t(`status.${value}` as "status.present") : "—";

  const loadReport = useCallback(async () => {
    if (!offeringId) return;
    setReportLoading(true);
    try {
      const anchor = selectedSession?.date || new Date().toISOString().slice(0, 10);
      setReport(await apiRequest<AttendanceReport>(`/attendance-records/report/?period=${reportPeriod}&date=${anchor}&offering=${offeringId}`));
    } catch { setError(true); }
    finally { setReportLoading(false); }
  }, [offeringId, reportPeriod, selectedSession?.date]);
  useEffect(() => { if (showReport) void loadReport(); }, [showReport, loadReport]);
  const loadPendingChanges = useCallback(async () => {
    if (user?.role !== "admin") return;
    try { setPendingChanges((await apiRequest<Paginated<PendingChange>>("/journal-changes/?status=pending&page_size=100")).results); }
    catch { setError(true); }
  }, [user?.role]);
  useEffect(() => { void loadPendingChanges(); }, [loadPendingChanges]);
  const reviewChange = async (id: number, decision: "approve" | "reject") => {
    try {
      await apiRequest(`/journal-changes/${id}/${decision}/`, { method: "POST", body: JSON.stringify({}) });
      await Promise.all([loadPendingChanges(), loadRows()]);
    } catch { setError(true); }
  };

  if (!user) return null;
  if (loading) return <LoadingPanel />;
  if (error && offerings.length === 0) return <ErrorPanel onRetry={loadOfferings} />;
  return (
    <div className="page page--journal">
      <header className="page-heading journal-heading">
        <div><span className="eyebrow">{readOnly ? t("role.student") : t("journal.eyebrow")}</span><h1>{readOnly ? t("journal.studentTitle") : t("journal.title")}</h1><p>{readOnly ? t("journal.studentSubtitle") : t("journal.subtitle")}</p></div>
        {!readOnly && <div className="journal-heading__actions">{user.role === "admin" && <button type="button" className={`button ${showApprovals ? "button--primary" : "button--secondary"}`} onClick={() => setShowApprovals((value) => !value)}><History size={17} />{t("journal.approvals")} {pendingChanges.length > 0 && <span className="button-count">{pendingChanges.length}</span>}</button>}<SaveIndicator state={saveState} /></div>}
      </header>
      <section className="journal-toolbar surface">
        <label className="field field--compact"><span>{t("journal.course")}</span><select value={offeringId ?? ""} onChange={(event) => setOfferingId(Number(event.target.value))} disabled={!offerings.length}>{offerings.map((item) => <option key={item.id} value={item.id}>{localizedOffering(item)} · {item.group_code}</option>)}</select></label>
        <label className="field field--compact"><span>{t("journal.session")}</span><select value={sessionId ?? ""} onChange={(event) => setSessionId(Number(event.target.value))} disabled={!sessions.length}>{sessions.map((item) => <option key={item.id} value={item.id}>{new Intl.DateTimeFormat(language === "tj" ? "tg-TJ" : language, { day: "2-digit", month: "short" }).format(new Date(`${item.date}T00:00:00`))} · {item.start_time.slice(0, 5)} · {item.topic}</option>)}</select></label>
        <label className="search-field"><Search size={18} /><span className="sr-only">{t("journal.search")}</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("journal.search")} /></label>
        <button type="button" className={`button ${showReport ? "button--primary" : "button--secondary"}`} onClick={() => setShowReport((value) => !value)}><BarChart3 size={18} />{t("journal.report")}</button>
        {!readOnly && <button type="button" className="button button--secondary" onClick={markAllPresent} disabled={!rows.length}><UserCheck size={18} />{t("journal.markAll")}</button>}
      </section>
      {selectedSession && <div className="session-context"><span className={`session-type session-type--${selectedSession.session_type}`}>{t(`session.${selectedSession.session_type}` as "session.lecture")}</span><strong>{selectedSession.topic}</strong><span>{selectedSession.room_label || "—"}</span><span>{t("journal.hours", { hours: selectedSession.academic_hours })}</span></div>}
      {showReport && <section className="journal-report surface"><header><div><span className="eyebrow">{t("journal.analytics")}</span><h2>{t("journal.reportTitle")}</h2>{report && <small>{report.start} — {report.end}</small>}</div><div className="period-switch">{(["day", "week", "month", "semester"] as ReportPeriod[]).map((period) => <button type="button" className={reportPeriod === period ? "is-active" : ""} key={period} onClick={() => setReportPeriod(period)}>{t(`period.${period}` as "period.day")}</button>)}</div></header>{reportLoading ? <LoadingPanel /> : report && <><div className="report-metrics"><article><span>{t("status.present")}</span><strong>{report.overall.present_hours}</strong><small>{t("journal.reportHours")}</small></article><article><span>{t("status.absent")}</span><strong>{report.overall.absent_hours}</strong><small>{t("journal.reportHours")}</small></article><article><span>{t("status.late")}</span><strong>{report.overall.late_hours}</strong><small>{t("journal.reportHours")}</small></article><article><span>{t("journal.gradeAverage")}</span><strong>{report.overall.average_grade ?? "—"}</strong><small>{report.overall.entries} {t("journal.entries")}</small></article></div><div className="report-table-wrap"><table className="data-table"><thead><tr><th>{t("journal.student")}</th><th>{t("status.present")}</th><th>{t("status.absent")}</th><th>{t("status.late")}</th><th>{t("status.excused")}</th><th>{t("journal.gradeAverage")}</th></tr></thead><tbody>{report.students.map((row) => <tr key={row.student_id}><td><strong>{row.student__user__last_name} {row.student__user__first_name}</strong><small>{row.student__student_id}</small></td><td>{row.present_hours}</td><td>{row.absent_hours}</td><td>{row.late_hours}</td><td>{row.excused_hours}</td><td><span className="grade-chip">{row.average_grade ?? "—"}</span></td></tr>)}</tbody></table></div></>}</section>}
      {showApprovals && user.role === "admin" && <section className="approval-panel surface"><header><div><span className="eyebrow">{t("journal.control")}</span><h2>{t("journal.approvalTitle")}</h2></div><span className="count-pill">{pendingChanges.length}</span></header>{pendingChanges.length ? <div className="approval-list">{pendingChanges.map((change) => <article key={change.id}><div className="approval-person"><strong>{change.student_name}</strong><small>{change.student_code} · {change.group_code} · {change.subject_name} · {change.session_date}</small></div><div className="approval-diff"><span>{localizedStatus(change.old_value.status)} → {localizedStatus(change.new_value.status)}</span><span>{t("journal.grade")}: {String(change.old_value.grade ?? "—")} → {String(change.new_value.grade ?? "—")}</span></div><p><strong>{t("journal.reason")}:</strong> {change.reason || "—"}<small>{change.author_name}</small></p><div><button type="button" className="button button--secondary button--small" onClick={() => void reviewChange(change.id, "reject")}><XCircle size={15} />{t("journal.reject")}</button><button type="button" className="button button--primary button--small" onClick={() => void reviewChange(change.id, "approve")}><Check size={15} />{t("journal.approve")}</button></div></article>)}</div> : <EmptyPanel>{t("journal.noApprovals")}</EmptyPanel>}</section>}
      {tableLoading ? <LoadingPanel /> : !offerings.length ? <EmptyPanel>{t("journal.noOfferings")}</EmptyPanel> : !sessions.length ? <EmptyPanel>{t("journal.noSessions")}</EmptyPanel> : !rows.length ? <EmptyPanel>{t("journal.noStudents")}</EmptyPanel> : (
        <section className="journal-workspace surface">
          <div className="journal-table-wrap">
            <table className="journal-table">
              <thead><tr><th className="student-sticky">{t("journal.student")}</th><th>{t("journal.attendance")}</th><th>{t("journal.grade")}</th><th>{t("journal.comment")}</th></tr></thead>
              <tbody>{filteredRows.map((row, index) => <tr key={row.student} className={row.is_confirmed ? "is-confirmed" : ""}><td className="student-sticky"><div className="student-cell"><span className="student-index">{String(index + 1).padStart(2, "0")}</span><div><strong>{row.student_detail.user.display_name}</strong><small>{row.student_detail.student_id}</small></div>{row.is_confirmed && <Check size={14} />}</div></td><td><StatusControl value={row.status} readOnly={readOnly} onChange={(value) => updateRow(row.student, "status", value)} /></td><td>{readOnly ? <strong className="grade-readonly">{row.grade ?? "—"}</strong> : <input className="grade-input" inputMode="decimal" data-grade-index={index} value={row.grade ?? ""} onKeyDown={(event) => gradeKeyDown(event, index)} onChange={(event) => updateRow(row.student, "grade", event.target.value)} aria-label={`${t("journal.grade")} — ${row.student_detail.user.display_name}`} />}</td><td>{readOnly ? <span className="comment-readonly">{row.comment || "—"}</span> : <input className="comment-input" value={row.comment} onChange={(event) => updateRow(row.student, "comment", event.target.value)} aria-label={`${t("journal.comment")} — ${row.student_detail.user.display_name}`} />}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="journal-mobile"><div className="journal-mobile__hint">{t("journal.mobileHint")}</div>{filteredRows.map((row, index) => <article className="journal-student-card" key={row.student}><header><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{row.student_detail.user.display_name}</strong><small>{row.student_detail.student_id}</small></div>{row.is_confirmed && <Check size={16} />}</header><StatusControl value={row.status} readOnly={readOnly} onChange={(value) => updateRow(row.student, "status", value)} /><div className="journal-student-card__fields"><label><span>{t("journal.grade")}</span>{readOnly ? <strong>{row.grade ?? "—"}</strong> : <input inputMode="decimal" value={row.grade ?? ""} onChange={(event) => updateRow(row.student, "grade", event.target.value)} />}</label><label><span>{t("journal.comment")}</span>{readOnly ? <strong>{row.comment || "—"}</strong> : <input value={row.comment} onChange={(event) => updateRow(row.student, "comment", event.target.value)} />}</label></div></article>)}</div>
          {!readOnly && <footer className="journal-footer"><label className="field correction-field"><span>{t("journal.reason")}</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder={t("journal.reasonHint")} /></label><div><SaveIndicator state={saveState} /><button type="button" className="button button--primary" onClick={confirmEntries} disabled={!rows.length || saveState === "saving"}><CheckCheck size={18} />{t("journal.confirm")}</button></div></footer>}
        </section>
      )}
    </div>
  );
}
