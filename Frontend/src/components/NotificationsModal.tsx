import { useState, useEffect } from "react";
import { Bell, AlertTriangle, CheckCircle, Info, ShieldAlert, X } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchNotifications } from "@/lib/api";

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  type: "urgent" | "warning" | "info" | "success";
  case_id?: string;
  read?: boolean;
}

interface NotificationsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NotificationsModal({ isOpen, onClose }: NotificationsModalProps) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      loadNotifications();
    }
  }, [isOpen]);

  const loadNotifications = async () => {
    setLoading(true);
    const data = await fetchNotifications();
    if (data && data.length > 0) {
      setNotifications(data);
    } else {
      // Fallback notifications if offline
      setNotifications([
        {
          id: "N-1",
          title: "Senior Citizen Bail Eligibility",
          message: "UTP-0007 (63 yrs, hypertensive) has completed half sentence.",
          timestamp: "10 mins ago",
          type: "urgent",
          case_id: "UTP-0007",
        },
        {
          id: "N-2",
          title: "Missing Document Alert",
          message: "UTP-0015 requires Charge Sheet for BNSS 479 draft generation.",
          timestamp: "45 mins ago",
          type: "warning",
          case_id: "UTP-0015",
        },
      ]);
    }
    setLoading(false);
  };

  if (!isOpen) return null;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const getIcon = (type: string) => {
    switch (type) {
      case "urgent":
        return <ShieldAlert className="w-5 h-5 text-destructive" />;
      case "warning":
        return <AlertTriangle className="w-5 h-5 text-amber-500" />;
      case "success":
        return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      default:
        return <Info className="w-5 h-5 text-accent" />;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end pt-16 pr-6 bg-black/40 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-background/95 border border-white/10 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl flex flex-col max-h-[80vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-accent" />
            <h3 className="font-semibold text-white tracking-tight">System Alerts & Notifications</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={markAllRead}
              className="text-xs text-muted-foreground hover:text-white transition-colors px-2 py-1 rounded hover:bg-white/5"
            >
              Mark all read
            </button>
            <button
              onClick={onClose}
              className="p-1 text-muted-foreground hover:text-white rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-4 overflow-y-auto space-y-3 flex-1">
          {loading ? (
            <div className="p-8 text-center text-sm text-muted-foreground animate-pulse">
              Loading alerts from Nyaya Mitra pipeline...
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              No new notifications.
            </div>
          ) : (
            notifications.map((item) => (
              <div
                key={item.id}
                className={`p-3.5 rounded-xl border transition-colors flex items-start gap-3 ${
                  item.read
                    ? "bg-white/[0.01] border-white/5 opacity-70"
                    : "bg-white/[0.03] border-white/10 hover:border-white/20"
                }`}
              >
                <div className="mt-0.5 shrink-0">{getIcon(item.type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-semibold text-white truncate">{item.title}</span>
                    <span className="text-[10px] text-muted-foreground shrink-0">{item.timestamp}</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed mb-2">{item.message}</p>
                  {item.case_id && (
                    <Link
                      to={`/case/${item.case_id}`}
                      onClick={onClose}
                      className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                    >
                      View Case {item.case_id} &rarr;
                    </Link>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
