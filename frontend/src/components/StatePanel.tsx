import { AlertCircle, Inbox, LoaderCircle } from "lucide-react";
import { ReactNode } from "react";
import { useI18n } from "../context/I18nContext";

export function LoadingPanel() {
  const { t } = useI18n();
  return <div className="state-panel" role="status"><LoaderCircle className="spin" /><span>{t("common.loading")}</span></div>;
}

export function ErrorPanel({ onRetry, message }: { onRetry?: () => void; message?: string }) {
  const { t } = useI18n();
  return (
    <div className="state-panel state-panel--error" role="alert">
      <AlertCircle />
      <span>{message || t("common.error")}</span>
      {onRetry && <button type="button" className="button button--secondary button--small" onClick={onRetry}>{t("common.retry")}</button>}
    </div>
  );
}

export function EmptyPanel({ children }: { children?: ReactNode }) {
  const { t } = useI18n();
  return <div className="state-panel state-panel--empty"><Inbox /><span>{children || t("common.noData")}</span></div>;
}

