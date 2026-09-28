import { AtSign, Languages, MoonStar, ShieldCheck, UserRound } from "lucide-react";
import { LanguageSwitch } from "../components/LanguageSwitch";
import { ThemeButton } from "../components/ThemeButton";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";

export function ProfilePage() {
  const { user } = useAuth();
  const { t } = useI18n();
  if (!user) return null;
  return (
    <div className="page">
      <header className="page-heading"><span className="eyebrow">{t("profile.eyebrow")}</span><h1>{t("profile.title")}</h1><p>{t("profile.subtitle")}</p></header>
      <section className="profile-card surface">
        <div className="profile-card__hero"><div className="avatar avatar--large" style={{ background: user.avatar_color }}>{user.first_name.slice(0, 1)}{user.last_name.slice(0, 1)}</div><div><h2>{user.display_name}</h2><span>{t(`role.${user.role}` as "role.admin")}</span></div></div>
        <dl className="profile-fields"><div><dt><UserRound />{t("profile.name")}</dt><dd>{user.display_name}</dd></div><div><dt><AtSign />{t("profile.email")}</dt><dd>{user.email}</dd></div><div><dt><ShieldCheck />{t("profile.role")}</dt><dd>{t(`role.${user.role}` as "role.admin")}</dd></div><div><dt><Languages />{t("language.label")}</dt><dd><LanguageSwitch /></dd></div><div><dt><MoonStar />{t("theme.label")}</dt><dd><ThemeButton /></dd></div></dl>
      </section>
    </div>
  );
}
