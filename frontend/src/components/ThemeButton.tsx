import { Moon, Sun } from "lucide-react";
import { useI18n } from "../context/I18nContext";
import { useTheme } from "../context/ThemeContext";

export function ThemeButton() {
  const { theme, toggleTheme } = useTheme();
  const { t } = useI18n();
  const label = theme === "light" ? t("theme.dark") : t("theme.light");
  return (
    <button type="button" className="icon-button" onClick={toggleTheme} aria-label={label} title={label}>
      {theme === "light" ? <Moon size={19} /> : <Sun size={19} />}
    </button>
  );
}

