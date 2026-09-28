import { Bell, BookOpenCheck, Building2, CalendarRange, Check, ChevronLeft, ClipboardCheck, FileUser, GraduationCap, LayoutDashboard, LogOut, Menu, PanelsTopLeft, ScrollText, Search, UserRound, X } from "lucide-react";
import { KeyboardEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { apiRequest } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";
import { Brand } from "./Brand";
import { LanguageSwitch } from "./LanguageSwitch";
import { ThemeButton } from "./ThemeButton";

type NotificationItem = { id: number; title: string; body: string; link: string; created_at: string; read_at: string | null };
type NotificationPage = { results: NotificationItem[] };

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [query, setQuery] = useState("");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const navigate = useNavigate();
  if (!user) return null;

  const nav = [
    { to: "/", icon: LayoutDashboard, label: t("nav.dashboard"), end: true },
    ...(user.role === "admin" ? [{ to: "/admissions", icon: FileUser, label: t("nav.admissions") }] : []),
    ...(user.role === "admin" ? [{ to: "/planning", icon: ScrollText, label: t("nav.planning") }] : []),
    { to: "/schedule", icon: CalendarRange, label: t("nav.schedule") },
    { to: "/journal", icon: BookOpenCheck, label: t("nav.journal") },
    { to: "/exams", icon: ClipboardCheck, label: user.role === "student" ? t("nav.transcript") : t("nav.exams") },
    { to: "/campus", icon: PanelsTopLeft, label: t("nav.campus") },
    ...(user.role === "admin" ? [{ to: "/structure", icon: Building2, label: t("nav.structure") }] : []),
    { to: "/profile", icon: UserRound, label: t("nav.profile") },
  ];
  const searchResults = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return normalized ? nav.filter((item) => item.label.toLocaleLowerCase().includes(normalized)) : [];
  }, [query, nav]);
  const unreadCount = notifications.filter((item) => !item.read_at).length;

  useEffect(() => {
    apiRequest<NotificationPage>("/notifications/?page_size=20").then((data) => setNotifications(data.results)).catch(() => setNotifications([]));
  }, [user.id]);

  const openSearchResult = (to: string) => { setQuery(""); navigate(to); };
  const searchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && searchResults[0]) openSearchResult(searchResults[0].to);
    if (event.key === "Escape") setQuery("");
  };
  const openNotification = async (item: NotificationItem) => {
    if (!item.read_at) {
      try {
        const updated = await apiRequest<NotificationItem>(`/notifications/${item.id}/mark-read/`, { method: "POST", body: JSON.stringify({}) });
        setNotifications((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
      } catch { /* The notification remains unread and can be retried. */ }
    }
    setNotificationsOpen(false);
    if (item.link.startsWith("/")) navigate(item.link);
  };

  return (
    <div className={`app-shell ${collapsed ? "app-shell--collapsed" : ""}`}>
      <button className="mobile-menu-button" type="button" onClick={() => setMobileOpen(true)} aria-label={t("nav.menu")}><Menu /></button>
      {mobileOpen && <button className="sidebar-scrim" type="button" onClick={() => setMobileOpen(false)} aria-label={t("nav.menu")} />}
      <aside className={`sidebar ${mobileOpen ? "sidebar--open" : ""}`}>
        <div className="sidebar__brand">
          <Brand compact={collapsed} />
          <button type="button" className="sidebar__mobile-close" onClick={() => setMobileOpen(false)} aria-label={t("nav.menu")}><X /></button>
        </div>
        <nav className="sidebar__nav" aria-label={t("nav.menu")}>
          {nav.map(({ to, icon: Icon, label, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setMobileOpen(false)} title={collapsed ? label : undefined}>
              <Icon size={20} /> <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__user">
          <div className="avatar" style={{ background: user.avatar_color }}>{user.first_name.slice(0, 1)}{user.last_name.slice(0, 1)}</div>
          {!collapsed && <div><strong>{user.display_name}</strong><small>{t(`role.${user.role}` as "role.admin")}</small></div>}
        </div>
        <button type="button" className="sidebar__logout" onClick={logout} title={collapsed ? t("nav.logout") : undefined}>
          <LogOut size={19} /><span>{t("nav.logout")}</span>
        </button>
        <button type="button" className="sidebar__collapse" onClick={() => setCollapsed((value) => !value)} aria-label={t("nav.menu")}>
          <ChevronLeft size={18} />
        </button>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div className="topbar__left"><div className="topbar__context"><GraduationCap size={18} /><span>{t("brand.product")}</span></div><div className="global-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={searchKeyDown} placeholder={t("nav.search")} aria-label={t("nav.search")} />{query && <div className="global-search__results">{searchResults.length ? searchResults.map(({ to, icon: Icon, label }) => <button type="button" key={to} onClick={() => openSearchResult(to)}><Icon size={16} /><span>{label}</span></button>) : <small>{t("nav.noSearchResults")}</small>}</div>}</div></div>
          <div className="topbar__tools"><div className="notification-center"><button className="icon-button notification-button" type="button" onClick={() => setNotificationsOpen((value) => !value)} aria-label={t("nav.notifications")}><Bell />{unreadCount > 0 && <span>{unreadCount > 9 ? "9+" : unreadCount}</span>}</button>{notificationsOpen && <div className="notification-panel surface"><header><strong>{t("nav.notifications")}</strong><small>{unreadCount} {t("nav.unread")}</small></header>{notifications.length ? notifications.map((item) => <button type="button" className={item.read_at ? "is-read" : ""} key={item.id} onClick={() => void openNotification(item)}><span>{item.read_at ? <Check size={14} /> : <Bell size={14} />}</span><div><strong>{item.title}</strong><small>{item.body}</small></div></button>) : <p>{t("nav.noNotifications")}</p>}</div>}</div><LanguageSwitch compact /><ThemeButton /></div>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
