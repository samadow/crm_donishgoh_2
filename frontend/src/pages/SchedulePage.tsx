import { CalendarPlus, Clock3, MapPin, Trash2, UserRound, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiRequest } from "../api/client";
import { EmptyPanel, ErrorPanel, LoadingPanel } from "../components/StatePanel";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";
import { Offering, Paginated, Room, ScheduleEntry } from "../types";

const today = new Date().toISOString().slice(0, 10);
const endDate = new Date(Date.now() + 120 * 86400000).toISOString().slice(0, 10);

export function SchedulePage() {
  const { user } = useAuth();
  const { t, language } = useI18n();
  const [entries, setEntries] = useState<ScheduleEntry[]>([]);
  const [offerings, setOfferings] = useState<Offering[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ offering: "", weekday: "0", start_time: "09:00", end_time: "10:30", room: "", effective_from: today, effective_to: endDate });

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [entryData, offeringData, roomData] = await Promise.all([
        apiRequest<Paginated<ScheduleEntry>>(`/schedule-entries/?is_active=true&page_size=100&ordering=weekday,start_time&lang=${language}`),
        apiRequest<Paginated<Offering>>(`/offerings/?is_active=true&page_size=100&lang=${language}`),
        apiRequest<Paginated<Room>>(`/rooms/?page_size=100`),
      ]);
      setEntries(entryData.results); setOfferings(offeringData.results); setRooms(roomData.results);
    } catch (caught) { setError(caught instanceof Error ? caught.message : t("common.error")); }
    finally { setLoading(false); }
  }, [language, t]);
  useEffect(() => { void load(); }, [load]);

  const localizedSubject = (entry: ScheduleEntry | Offering) => {
    if ("group_code" in entry && "weekday" in entry) return language === "tj" ? entry.subject_name_tj : language === "en" ? entry.subject_name_en : entry.subject_name;
    return language === "tj" ? entry.subject_name_tj : language === "en" ? entry.subject_name_en : entry.subject_name;
  };
  const byDay = useMemo(() => Array.from({ length: 6 }, (_, day) => entries.filter((entry) => entry.weekday === day)), [entries]);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await apiRequest("/schedule-entries/", { method: "POST", body: JSON.stringify({ ...form, offering: Number(form.offering), weekday: Number(form.weekday), room: Number(form.room), is_active: true }) });
      setShowForm(false); await load();
    } catch (caught) { setError(caught instanceof ApiError && caught.status === 409 ? t("schedule.conflict") : caught instanceof Error ? caught.message : t("common.error")); }
    finally { setBusy(false); }
  };

  const remove = async (id: number) => {
    setBusy(true); setError("");
    try { await apiRequest(`/schedule-entries/${id}/`, { method: "DELETE" }); await load(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : t("common.error")); }
    finally { setBusy(false); }
  };

  if (!user) return null;
  if (loading && !entries.length) return <LoadingPanel />;
  if (error && !entries.length) return <ErrorPanel onRetry={load} message={error} />;
  return (
    <div className="page">
      <header className="page-heading page-heading--actions"><div><span className="eyebrow">{t("schedule.eyebrow")}</span><h1>{t("schedule.title")}</h1><p>{t("schedule.subtitle")}</p></div>{user.role === "admin" && <button className="button button--primary" type="button" onClick={() => setShowForm(true)}><CalendarPlus size={18} />{t("schedule.add")}</button>}</header>
      {error && <div className="inline-notice inline-notice--error">{error}<button type="button" onClick={() => setError("")}><X size={15} /></button></div>}
      <section className="schedule-board">
        {byDay.map((dayEntries, day) => <article className="schedule-day surface" key={day}><header><span>{String(day + 1).padStart(2, "0")}</span><h2>{t(`day.${day}` as "day.0")}</h2><small>{dayEntries.length}</small></header><div>{dayEntries.length === 0 ? <EmptyPanel>{t("schedule.empty")}</EmptyPanel> : dayEntries.map((entry) => <div className="schedule-card" key={entry.id}><div className="schedule-card__time"><Clock3 size={15} />{entry.start_time.slice(0, 5)}–{entry.end_time.slice(0, 5)}</div><strong>{localizedSubject(entry)}</strong><span>{entry.group_code}</span><div className="schedule-card__meta"><span><MapPin size={13} />{entry.room_label}</span><span><UserRound size={13} />{entry.teacher_name}</span></div>{user.role === "admin" && <button className="schedule-card__delete" type="button" disabled={busy} onClick={() => void remove(entry.id)} aria-label={t("admissions.cancel")}><Trash2 size={14} /></button>}</div>)}</div></article>)}
      </section>

      {showForm && <div className="dialog-backdrop"><form className="dialog surface" onSubmit={submit}><header><div><span className="eyebrow">{t("schedule.eyebrow")}</span><h2>{t("schedule.add")}</h2></div><button className="icon-button" type="button" onClick={() => setShowForm(false)}><X /></button></header><div className="form-grid"><label className="field form-grid__wide"><span>{t("schedule.course")}</span><select required value={form.offering} onChange={(event) => setForm({ ...form, offering: event.target.value })}><option value="" />{offerings.map((offering) => <option key={offering.id} value={offering.id}>{localizedSubject(offering)} · {offering.group_code} · {offering.teacher_name}</option>)}</select></label><label className="field"><span>{t("schedule.weekday")}</span><select value={form.weekday} onChange={(event) => setForm({ ...form, weekday: event.target.value })}>{Array.from({ length: 6 }, (_, day) => <option key={day} value={day}>{t(`day.${day}` as "day.0")}</option>)}</select></label><label className="field"><span>{t("schedule.room")}</span><select required value={form.room} onChange={(event) => setForm({ ...form, room: event.target.value })}><option value="" />{rooms.map((room) => <option key={room.id} value={room.id}>{room.building} · {room.code} ({room.capacity})</option>)}</select></label><label className="field"><span>{t("schedule.start")}</span><input type="time" required value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} /></label><label className="field"><span>{t("schedule.end")}</span><input type="time" required value={form.end_time} onChange={(event) => setForm({ ...form, end_time: event.target.value })} /></label><label className="field"><span>{t("schedule.from")}</span><input type="date" required value={form.effective_from} onChange={(event) => setForm({ ...form, effective_from: event.target.value })} /></label><label className="field"><span>{t("schedule.to")}</span><input type="date" required value={form.effective_to} onChange={(event) => setForm({ ...form, effective_to: event.target.value })} /></label></div><footer><button className="button button--secondary" type="button" onClick={() => setShowForm(false)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy} type="submit">{t("schedule.save")}</button></footer></form></div>}
    </div>
  );
}

