import { ArrowRight, BookOpenCheck, LockKeyhole, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { Brand } from "../components/Brand";
import { LanguageSwitch } from "../components/LanguageSwitch";
import { ThemeButton } from "../components/ThemeButton";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";
import { Role } from "../types";

const accounts: Array<{ role: Role; email: string; password: string }> = [
  { role: "admin", email: "admin@orion.tj", password: "DemoAdmin!2026" },
  { role: "teacher", email: "teacher@orion.tj", password: "DemoTeacher!2026" },
  { role: "student", email: "student@orion.tj", password: "DemoStudent!2026" },
];

export function LoginPage() {
  const { login, user } = useAuth();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/" replace />;

  const signIn = async (nextEmail: string, nextPassword: string) => {
    setError("");
    setBusy(true);
    try {
      await login(nextEmail, nextPassword);
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status !== 401 ? caught.message : t("login.error"));
    } finally {
      setBusy(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void signIn(email, password);
  };

  return (
    <div className="login-page">
      <section className="login-visual">
        <div className="login-visual__image" />
        <div className="login-visual__veil" />
        <div className="login-visual__top"><Brand /><div><LanguageSwitch /><ThemeButton /></div></div>
        <div className="login-visual__copy">
          <span className="eyebrow eyebrow--on-dark"><BookOpenCheck size={16} />{t("login.eyebrow")}</span>
          <h1>{t("login.title")}</h1>
          <p>{t("login.body")}</p>
        </div>
        <div className="login-visual__seal"><ShieldCheck /><span>{t("login.secure")}</span></div>
      </section>
      <section className="login-panel">
        <div className="login-panel__mobile-brand"><Brand /><div><LanguageSwitch compact /><ThemeButton /></div></div>
        <form className="login-card" onSubmit={submit}>
          <span className="login-card__icon"><LockKeyhole /></span>
          <h2>{t("login.cardTitle")}</h2>
          <p>{t("login.cardBody")}</p>
          <label className="field">
            <span>{t("login.email")}</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required placeholder="name@university.tj" />
          </label>
          <label className="field">
            <span>{t("login.password")}</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
          </label>
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="button button--primary button--wide" disabled={busy} type="submit">
            {busy ? t("login.loading") : t("login.submit")} {!busy && <ArrowRight size={18} />}
          </button>
          <div className="demo-accounts">
            <span>{t("login.demo")}</span>
            {accounts.map((account) => (
              <button key={account.role} type="button" disabled={busy} onClick={() => void signIn(account.email, account.password)}>
                <span className={`role-dot role-dot--${account.role}`} />
                <span><strong>{t(`role.${account.role}` as "role.admin")}</strong><small>{account.email}</small></span>
                <ArrowRight size={16} />
              </button>
            ))}
          </div>
        </form>
      </section>
    </div>
  );
}

