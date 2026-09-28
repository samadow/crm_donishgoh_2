import { BookOpen, Building2, DoorOpen, GraduationCap, Layers3, Plus, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest } from "../api/client";
import { EmptyPanel, ErrorPanel, LoadingPanel } from "../components/StatePanel";
import { useI18n } from "../context/I18nContext";
import { Faculty, Group, Paginated, Program, Room, Subject, TeacherSummary } from "../types";

export function StructurePage() {
  const { t, language } = useI18n();
  const [faculties, setFaculties] = useState<Faculty[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [teachers, setTeachers] = useState<TeacherSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dialog, setDialog] = useState<"faculty" | "program" | "group" | "subject" | "room" | null>(null);
  const [facultyForm, setFacultyForm] = useState({ code: "", name_tj: "", name_ru: "", name_en: "" });
  const [programForm, setProgramForm] = useState({ faculty: "", code: "", name_tj: "", name_ru: "", name_en: "", degree: "bachelor", duration_years: "4" });
  const [groupForm, setGroupForm] = useState({ program: "", code: "", admission_year: String(new Date().getFullYear()), course: "1", curator: "" });
  const [subjectForm, setSubjectForm] = useState({ code: "", name_tj: "", name_ru: "", name_en: "", credits: "5" });
  const [roomForm, setRoomForm] = useState({ code: "", building: "", capacity: "30", room_type: "classroom", is_accessible: false });
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [facultyData, groupData, programData, subjectData, roomData, teacherData] = await Promise.all([
        apiRequest<Paginated<Faculty>>(`/faculties/?page_size=100&lang=${language}`),
        apiRequest<Paginated<Group>>(`/groups/?page_size=100&lang=${language}`),
        apiRequest<Paginated<Program>>(`/programs/?page_size=100&lang=${language}`),
        apiRequest<Paginated<Subject>>(`/subjects/?page_size=100&lang=${language}`),
        apiRequest<Paginated<Room>>("/rooms/?page_size=100"),
        apiRequest<Paginated<TeacherSummary>>("/teachers/?page_size=100"),
      ]);
      setFaculties(facultyData.results); setGroups(groupData.results); setPrograms(programData.results); setSubjects(subjectData.results); setRooms(roomData.results); setTeachers(teacherData.results);
    } catch { setError(t("common.error")); } finally { setLoading(false); }
  }, [language, t]);
  useEffect(() => { void load(); }, [load]);

  const createStructure = async (event: FormEvent) => {
    event.preventDefault(); if (!dialog) return; setBusy(true); setError("");
    const requests = {
      faculty: ["/faculties/", facultyForm],
      program: ["/programs/", { ...programForm, faculty: Number(programForm.faculty), duration_years: Number(programForm.duration_years) }],
      group: ["/groups/", { ...groupForm, program: Number(groupForm.program), admission_year: Number(groupForm.admission_year), course: Number(groupForm.course), curator: groupForm.curator ? Number(groupForm.curator) : null, is_active: true }],
      subject: ["/subjects/", subjectForm],
      room: ["/rooms/", { ...roomForm, capacity: Number(roomForm.capacity) }],
    } as const;
    try { const [path, body] = requests[dialog]; await apiRequest(path, { method: "POST", body: JSON.stringify(body) }); setDialog(null); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : t("common.error")); } finally { setBusy(false); }
  };
  const programName = (program: Program) => language === "tj" ? program.name_tj : language === "en" ? program.name_en : program.name_ru;

  if (loading) return <LoadingPanel />;
  if (error && !faculties.length) return <ErrorPanel onRetry={load} message={error} />;
  return (
    <div className="page">
      <header className="page-heading"><span className="eyebrow">{t("structure.eyebrow")}</span><h1>{t("structure.title")}</h1><p>{t("structure.subtitle")}</p></header>
      {error && <div className="inline-notice inline-notice--error">{error}<button type="button" onClick={() => setError("")}><X size={15} /></button></div>}
      <div className="structure-actions surface">{(["faculty", "program", "group", "subject", "room"] as const).map((kind) => <button className="button button--secondary button--small" type="button" key={kind} onClick={() => setDialog(kind)}><Plus size={15} />{t(`structure.add.${kind}` as "structure.add.faculty")}</button>)}</div>
      <div className="structure-grid">
        <section className="surface directory-card"><div className="section-heading"><h2><Building2 />{t("structure.faculties")}</h2><span className="count-pill">{faculties.length}</span></div>{faculties.length ? <div className="directory-list">{faculties.map((faculty) => <div key={faculty.id}><span className="code-badge">{faculty.code}</span><strong>{faculty.name}</strong></div>)}</div> : <EmptyPanel />}</section>
        <section className="surface directory-card directory-card--wide"><div className="section-heading"><h2><GraduationCap />{t("structure.groups")}</h2><span className="count-pill">{groups.length}</span></div>{groups.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr><th>{t("structure.code")}</th><th>{t("structure.program")}</th><th>{t("structure.course")}</th><th>{t("structure.curator")}</th><th>{t("structure.students")}</th></tr></thead><tbody>{groups.map((group) => <tr key={group.id}><td><strong>{group.code}</strong></td><td>{language === "tj" ? group.program_name_tj : language === "en" ? group.program_name_en : group.program_name}</td><td>{group.course}</td><td>{group.curator_name || "—"}</td><td>{group.student_count}</td></tr>)}</tbody></table></div> : <EmptyPanel />}</section>
      </div>
      <div className="structure-catalogs">
        <section className="surface directory-card"><div className="section-heading"><h2><Layers3 />{t("structure.programs")}</h2><span className="count-pill">{programs.length}</span></div><div className="directory-list">{programs.slice(0, 8).map((program) => <div key={program.id}><span className="code-badge">{program.code}</span><strong>{programName(program)}</strong></div>)}</div></section>
        <section className="surface directory-card"><div className="section-heading"><h2><BookOpen />{t("structure.subjects")}</h2><span className="count-pill">{subjects.length}</span></div><div className="directory-list">{subjects.slice(0, 8).map((subject) => <div key={subject.id}><span className="code-badge">{subject.code}</span><strong>{subject.name}</strong></div>)}</div></section>
        <section className="surface directory-card"><div className="section-heading"><h2><DoorOpen />{t("structure.rooms")}</h2><span className="count-pill">{rooms.length}</span></div><div className="directory-list">{rooms.slice(0, 8).map((room) => <div key={room.id}><span className="code-badge">{room.code}</span><strong>{room.building} · {room.capacity}</strong></div>)}</div></section>
      </div>
      {dialog === "faculty" && <div className="dialog-backdrop"><form className="dialog dialog--small surface" onSubmit={createStructure}><header><h2>{t("structure.add.faculty")}</h2><button className="icon-button" type="button" onClick={() => setDialog(null)}><X /></button></header><label className="field"><span>{t("structure.code")}</span><input required value={facultyForm.code} onChange={(event) => setFacultyForm({ ...facultyForm, code: event.target.value })} /></label>{(["name_tj", "name_ru", "name_en"] as const).map((field) => <label className="field" key={field}><span>{t(`structure.${field}` as "structure.name_tj")}</span><input required value={facultyForm[field]} onChange={(event) => setFacultyForm({ ...facultyForm, [field]: event.target.value })} /></label>)}<footer><button className="button button--secondary" type="button" onClick={() => setDialog(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy}>{t("journal.save")}</button></footer></form></div>}
      {dialog === "program" && <div className="dialog-backdrop"><form className="dialog surface" onSubmit={createStructure}><header><h2>{t("structure.add.program")}</h2><button className="icon-button" type="button" onClick={() => setDialog(null)}><X /></button></header><div className="form-grid"><label className="field"><span>{t("structure.faculties")}</span><select required value={programForm.faculty} onChange={(event) => setProgramForm({ ...programForm, faculty: event.target.value })}><option value="" />{faculties.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select></label><label className="field"><span>{t("structure.code")}</span><input required value={programForm.code} onChange={(event) => setProgramForm({ ...programForm, code: event.target.value })} /></label>{(["name_tj", "name_ru", "name_en"] as const).map((field) => <label className="field" key={field}><span>{t(`structure.${field}` as "structure.name_tj")}</span><input required value={programForm[field]} onChange={(event) => setProgramForm({ ...programForm, [field]: event.target.value })} /></label>)}<label className="field"><span>{t("structure.degree")}</span><select value={programForm.degree} onChange={(event) => setProgramForm({ ...programForm, degree: event.target.value })}><option value="bachelor">{t("structure.bachelor")}</option><option value="master">{t("structure.master")}</option><option value="phd">{t("structure.phd")}</option></select></label><label className="field"><span>{t("structure.duration")}</span><input type="number" min="1" max="8" required value={programForm.duration_years} onChange={(event) => setProgramForm({ ...programForm, duration_years: event.target.value })} /></label></div><footer><button className="button button--secondary" type="button" onClick={() => setDialog(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy}>{t("journal.save")}</button></footer></form></div>}
      {dialog === "group" && <div className="dialog-backdrop"><form className="dialog dialog--small surface" onSubmit={createStructure}><header><h2>{t("structure.add.group")}</h2><button className="icon-button" type="button" onClick={() => setDialog(null)}><X /></button></header><label className="field"><span>{t("structure.program")}</span><select required value={groupForm.program} onChange={(event) => setGroupForm({ ...groupForm, program: event.target.value })}><option value="" />{programs.map((item) => <option key={item.id} value={item.id}>{item.code} · {programName(item)}</option>)}</select></label><label className="field"><span>{t("structure.code")}</span><input required value={groupForm.code} onChange={(event) => setGroupForm({ ...groupForm, code: event.target.value })} /></label><label className="field"><span>{t("structure.admissionYear")}</span><input type="number" required value={groupForm.admission_year} onChange={(event) => setGroupForm({ ...groupForm, admission_year: event.target.value })} /></label><label className="field"><span>{t("structure.course")}</span><input type="number" min="1" max="8" required value={groupForm.course} onChange={(event) => setGroupForm({ ...groupForm, course: event.target.value })} /></label><label className="field"><span>{t("structure.curator")}</span><select value={groupForm.curator} onChange={(event) => setGroupForm({ ...groupForm, curator: event.target.value })}><option value="" />{teachers.map((item) => <option key={item.id} value={item.id}>{item.user.display_name}</option>)}</select></label><footer><button className="button button--secondary" type="button" onClick={() => setDialog(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy}>{t("journal.save")}</button></footer></form></div>}
      {dialog === "subject" && <div className="dialog-backdrop"><form className="dialog dialog--small surface" onSubmit={createStructure}><header><h2>{t("structure.add.subject")}</h2><button className="icon-button" type="button" onClick={() => setDialog(null)}><X /></button></header><label className="field"><span>{t("structure.code")}</span><input required value={subjectForm.code} onChange={(event) => setSubjectForm({ ...subjectForm, code: event.target.value })} /></label>{(["name_tj", "name_ru", "name_en"] as const).map((field) => <label className="field" key={field}><span>{t(`structure.${field}` as "structure.name_tj")}</span><input required value={subjectForm[field]} onChange={(event) => setSubjectForm({ ...subjectForm, [field]: event.target.value })} /></label>)}<label className="field"><span>{t("planning.credits")}</span><input type="number" min="0" step=".5" required value={subjectForm.credits} onChange={(event) => setSubjectForm({ ...subjectForm, credits: event.target.value })} /></label><footer><button className="button button--secondary" type="button" onClick={() => setDialog(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy}>{t("journal.save")}</button></footer></form></div>}
      {dialog === "room" && <div className="dialog-backdrop"><form className="dialog dialog--small surface" onSubmit={createStructure}><header><h2>{t("structure.add.room")}</h2><button className="icon-button" type="button" onClick={() => setDialog(null)}><X /></button></header><label className="field"><span>{t("structure.code")}</span><input required value={roomForm.code} onChange={(event) => setRoomForm({ ...roomForm, code: event.target.value })} /></label><label className="field"><span>{t("structure.building")}</span><input required value={roomForm.building} onChange={(event) => setRoomForm({ ...roomForm, building: event.target.value })} /></label><label className="field"><span>{t("structure.capacity")}</span><input type="number" min="1" required value={roomForm.capacity} onChange={(event) => setRoomForm({ ...roomForm, capacity: event.target.value })} /></label><label className="field"><span>{t("structure.roomType")}</span><select value={roomForm.room_type} onChange={(event) => setRoomForm({ ...roomForm, room_type: event.target.value })}><option value="classroom">{t("structure.classroom")}</option><option value="computer_lab">{t("structure.computerLab")}</option><option value="laboratory">{t("structure.laboratory")}</option></select></label><label className="check-field"><input type="checkbox" checked={roomForm.is_accessible} onChange={(event) => setRoomForm({ ...roomForm, is_accessible: event.target.checked })} /><span>{t("structure.accessible")}</span></label><footer><button className="button button--secondary" type="button" onClick={() => setDialog(null)}>{t("admissions.cancel")}</button><button className="button button--primary" disabled={busy}>{t("journal.save")}</button></footer></form></div>}
    </div>
  );
}

