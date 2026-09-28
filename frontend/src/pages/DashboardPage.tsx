import { AlertTriangle, ArrowUpRight, BookOpen, CalendarDays, Clock3, GraduationCap, Layers3, UsersRound } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../api/client";
import { EmptyPanel, ErrorPanel, LoadingPanel } from "../components/StatePanel";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";
import { DashboardData } from "../types";

const statIcons = { students: GraduationCap, teachers: UsersRound, groups: Layers3, today_sessions: CalendarDays, courses: BookOpen, open_entries: Clock3, subjects: BookOpen, missed_hours: Clock3, grade_average: GraduationCap };

export function DashboardPage() {
  const { user } = useAuth();
  const { t, language } = useI18n();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setError(false);
    try { setData(await apiRequest<DashboardData>(`/dashboard/?lang=${language}`)); } catch { setError(true); }
  }, [language]);

  useEffect(() => { void load(); }, [load]);
  if (!user) return null;
  if (error) return <ErrorPanel onRetry={load} />;
  if (!data) return <LoadingPanel />;
  const lead = user.role === "admin" ? "dashboard.adminLead" : user.role === "teacher" ? "dashboard.teacherLead" : "dashboard.studentLead";

  return (
    <div className="page page--dashboard">
      <header className="page-heading">
        <span className="eyebrow">{t("dashboard.eyebrow")}</span>
        <h1>{t("dashboard.greeting", { name: user.first_name || user.display_name })}</h1>
        <p>{t(lead)}</p>
      </header>
      <section className="stat-grid">
        {Object.entries(data.stats).map(([key, value], index) => {
          const Icon = statIcons[key as keyof typeof statIcons] || Layers3;
          return <article className={`stat-card stat-card--${index + 1}`} key={key}><span><Icon /></span><strong>{value ?? "—"}</strong><small>{t(`dashboard.${key}` as "dashboard.students")}</small></article>;
        })}
      </section>
      <div className="dashboard-grid">
        <section className="surface schedule-panel">
          <div className="section-heading"><div><span className="eyebrow">{t("dashboard.today")}</span><h2>{t("dashboard.today_sessions")}</h2></div><Link className="text-link" to="/journal">{t("dashboard.openJournal")}<ArrowUpRight size={16} /></Link></div>
          {data.today.length === 0 ? <EmptyPanel>{t("dashboard.noClasses")}</EmptyPanel> : (
            <div className="session-list">{data.today.map((session) => <article className="session-row" key={session.id}><time>{session.start_time.slice(0, 5)}</time><span className="session-row__line" /><div><strong>{language === "tj" ? session.offering_detail.subject_name_tj : language === "en" ? session.offering_detail.subject_name_en : session.offering_detail.subject_name}</strong><span>{session.offering_detail.group_code} · {session.room_label || "—"}</span><small>{session.topic}</small></div><span className={`session-type session-type--${session.session_type}`}>{t(`session.${session.session_type}` as "session.lecture")}</span></article>)}</div>
          )}
        </section>
        <aside className="surface attention-panel">
          <div className="section-heading"><div><span className="eyebrow">{t("dashboard.signal")}</span><h2>{t("dashboard.attention")}</h2></div><AlertTriangle /></div>
          {data.alerts.length === 0 ? <div className="calm-state"><span>✓</span><p>{t("common.noData")}</p></div> : data.alerts.map((alert, index) => <div className="alert-item" key={index}><AlertTriangle /><p>{alert.key === "unmarked_sessions" ? t("dashboard.unmarked", { count: alert.count }) : t("dashboard.threshold", { threshold: alert.threshold })}</p></div>)}
        </aside>
      </div>
    </div>
  );
}
