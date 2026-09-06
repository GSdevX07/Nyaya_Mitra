import React, { useEffect } from "react";
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X, RefreshCw } from "lucide-react";

export interface ToastItem {
  id: string;
  type: "success" | "warning" | "error" | "conflict" | "info";
  title: string;
  message: string;
  timestamp?: number;
}

export interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map((t) =>
      setTimeout(() => {
        onDismiss(t.id);
      }, 5500)
    );
    return () => {
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [toasts, onDismiss]);

  if (toasts.length === 0) return null;

  const getTypeConfig = (type: ToastItem["type"]) => {
    switch (type) {
      case "success":
        return {
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />,
          accentBorder: "border-l-4 border-l-emerald-600",
          badgeClass: "bg-emerald-100 text-emerald-900 border-emerald-300",
          badgeLabel: "Success",
        };
      case "conflict":
        return {
          icon: <RefreshCw className="w-4 h-4 text-amber-700 shrink-0" />,
          accentBorder: "border-l-4 border-l-amber-600",
          badgeClass: "bg-amber-100 text-amber-900 border-amber-300",
          badgeLabel: "Notice",
        };
      case "warning":
        return {
          icon: <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />,
          accentBorder: "border-l-4 border-l-amber-600",
          badgeClass: "bg-amber-100 text-amber-900 border-amber-300",
          badgeLabel: "Notice",
        };
      case "error":
        return {
          icon: <AlertCircle className="w-4 h-4 text-rose-700 shrink-0" />,
          accentBorder: "border-l-4 border-l-rose-600",
          badgeClass: "bg-rose-100 text-rose-900 border-rose-300",
          badgeLabel: "Attention",
        };
      case "info":
      default:
        return {
          icon: <Info className="w-4 h-4 text-foreground shrink-0" />,
          accentBorder: "border-l-4 border-l-primary",
          badgeClass: "bg-secondary text-secondary-foreground border-border",
          badgeLabel: "Info",
        };
    }
  };

  return (
    <div className="fixed top-5 right-5 z-[99999] flex flex-col gap-2.5 max-w-sm sm:max-w-md w-full pointer-events-none p-3 sm:p-0">
      {toasts.map((toast) => {
        const config = getTypeConfig(toast.type);
        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 p-3.5 bg-card text-foreground border border-border rounded-sm shadow-lg transition-all duration-200 animate-in slide-in-from-top-2 fade-in duration-150 ${config.accentBorder}`}
            role="status"
            aria-live="polite"
          >
            <div className="mt-0.5">{config.icon}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h4 className="text-xs font-bold text-foreground tracking-wide font-sans">{toast.title}</h4>
                <span className={`text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded-sm border ${config.badgeClass}`}>
                  {config.badgeLabel}
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed font-sans">{toast.message}</p>
            </div>
            <button
              onClick={() => onDismiss(toast.id)}
              className="text-muted-foreground hover:text-foreground hover:bg-secondary/50 p-1 rounded-sm transition-colors shrink-0"
              aria-label="Dismiss notification"
            >
              <X className="w-3.5 h-3.5 opacity-70 hover:opacity-100" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
