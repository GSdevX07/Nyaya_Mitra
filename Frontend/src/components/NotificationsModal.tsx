import { Bell, AlertTriangle, CheckCircle, Info, ShieldAlert, X, Trash2, BellOff, CheckCheck } from "lucide-react";
import { Link } from "react-router-dom";

export interface NotificationItem {
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
  notifications: NotificationItem[];
  onMarkAllRead: () => void;
  onMarkItemRead: (id: string) => void;
  onClearAll?: () => void;
  onClearItem?: (id: string) => void;
  loading?: boolean;
}

export function NotificationsModal({
  isOpen,
  onClose,
  notifications,
  onMarkAllRead,
  onMarkItemRead,
  onClearAll,
  onClearItem,
  loading = false,
}: NotificationsModalProps) {
  if (!isOpen) return null;

  const getIcon = (type: string) => {
    switch (type) {
      case "urgent":
        return <ShieldAlert className="w-5 h-5 text-destructive" />;
      case "warning":
        return <AlertTriangle className="w-5 h-5 text-muted-foreground" />;
      case "success":
        return <CheckCircle className="w-5 h-5 text-foreground" />;
      default:
        return <Info className="w-5 h-5 text-accent" />;
    }
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end pt-16 pr-6 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="notifications-dialog-title"
        className="w-full max-w-md bg-background/95 border border-border rounded shadow-2xl overflow-hidden backdrop-blur-xl flex flex-col max-h-[80vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-border flex items-center justify-between bg-card shadow-sm">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-accent" />
            <h3 id="notifications-dialog-title" className="font-semibold text-primary tracking-tight">
              System Alerts & Notifications
            </h3>
            {unreadCount > 0 && (
              <span className="text-[10px] bg-destructive/20 text-destructive border border-destructive/30 px-1.5 py-0.5 rounded-sm font-mono font-bold">
                {unreadCount} unread
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={onMarkAllRead}
                className="text-xs text-accent hover:text-foreground transition-colors px-2 py-1 rounded hover:bg-secondary/50 font-medium flex items-center gap-1"
                title="Mark all notifications as read"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>Mark read</span>
              </button>
            )}
            {notifications.length > 0 && onClearAll && (
              <button
                type="button"
                onClick={onClearAll}
                className="text-xs text-rose-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors px-2 py-1 rounded font-medium flex items-center gap-1"
                title="Clear all notifications"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear all</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1 text-muted-foreground hover:text-foreground rounded-sm hover:bg-secondary transition-colors ml-1"
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
            <div className="py-12 px-6 text-center flex flex-col items-center justify-center gap-3 text-muted-foreground">
              <div className="w-12 h-12 rounded-full bg-secondary/60 flex items-center justify-center text-muted-foreground">
                <BellOff className="w-6 h-6 opacity-60" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">All notifications cleared</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-[260px] leading-relaxed">
                  You are caught up. There are no pending alerts or case notifications for your workspace.
                </p>
              </div>
            </div>
          ) : (
            notifications.map((item) => (
              <div
                key={item.id}
                onClick={() => onMarkItemRead(item.id)}
                className={`group p-3.5 rounded border transition-all cursor-pointer flex items-start gap-3 relative ${
                  item.read
                    ? "bg-card shadow-sm border-border opacity-60 hover:opacity-80"
                    : "bg-card/80 border-accent/20 hover:border-accent/40 shadow-sm"
                }`}
              >
                <div className="mt-0.5 shrink-0">{getIcon(item.type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2 truncate">
                      <span className="text-xs font-semibold text-primary truncate">
                        {item.title}
                      </span>
                      {!item.read && (
                        <span className="w-1.5 h-1.5 rounded-sm bg-accent shrink-0" />
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-[10px] text-muted-foreground">
                        {item.timestamp}
                      </span>
                      {onClearItem && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onClearItem(item.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 hover:text-rose-500 hover:bg-rose-500/10 p-1 rounded transition-all"
                          title="Dismiss notification"
                        >
                          <Trash2 className="w-3 h-3 text-muted-foreground hover:text-rose-500" />
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed mb-2">
                    {item.message}
                  </p>
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

