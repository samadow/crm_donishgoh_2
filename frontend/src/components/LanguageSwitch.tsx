import { Languages } from "lucide-react";
import { useI18n } from "../context/I18nContext";
import { Language } from "../types";

const languages: Array<{ value: Language; label: string }> = [
  { value: "tj", label: "Тоҷикӣ" },
  { value: "ru", label: "Русский" },
  { value: "en", label: "English" },
];

export function LanguageSwitch({ compact = false }: { compact?: boolean }) {
  const { language, setLanguage, t } = useI18n();
  return (
    <label className={`language-switch ${compact ? "language-switch--compact" : ""}`}>
      <Languages size={17} aria-hidden="true" />
      <span className="sr-only">{t("language.label")}</span>
      <select value={language} onChange={(event) => setLanguage(event.target.value as Language)} aria-label={t("language.label")}>
        {languages.map((item) => <option key={item.value} value={item.value}>{compact ? item.value.toUpperCase() : item.label}</option>)}
      </select>
    </label>
  );
}

