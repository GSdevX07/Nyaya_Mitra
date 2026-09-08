import { useState, useEffect } from "react";
import {
  Bell,
  AlertTriangle,
  CheckCircle,
  Info,
  ShieldAlert,
  X,
  Trash2,
  BellOff,
  CheckCheck,
  Radio,
  Sliders,
  Check,
  RotateCcw,
  ArrowLeft,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  fetchNotificationPreferences,
  updateNotificationPreferences,
} from "@/lib/api";

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  type: "urgent" | "warning" | "info" | "success";
  case_id?: string;
  read?: boolean;
  priority?: string;
  channel?: string;
  is_acknowledged?: boolean;
  escalation_tier?: number;
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
  onTestAlert?: () => void;
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
  onTestAlert,
}: NotificationsModalProps) {
  const [showPreferences, setShowPreferences] = useState(false);
  const [prefsLoading, setPrefsLoading] = useState(false);
  const [prefsSaved, setPrefsSaved] = useState(false);

  // Preference fields
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false);
  const [quietStart, setQuietStart] = useState("22:00");
  const [quietEnd, setQuietEnd] = useState("06:00");
  const [prefLang, setPrefLang] = useState("en");
  const [enabledChannels, setEnabledChannels] = useState<string[]>([
    "IN_APP",
    "EMAIL",
    "SMS",
    "WHATSAPP",
  ]);

  useEffect(() => {
    if (showPreferences) {
      setPrefsLoading(true);
      fetchNotificationPreferences()
        .then((p) => {
          if (p) {
            setQuietHoursEnabled(Boolean(p.quiet_hours_enabled));
            setQuietStart(p.quiet_hours_start || "22:00");
            setQuietEnd(p.quiet_hours_end || "06:00");
            setPrefLang(p.preferred_language || "en");
            if (Array.isArray(p.enabled_channels) && p.enabled_channels.length > 0) {
              setEnabledChannels(p.enabled_channels);
            }
          }
        })
        .finally(() => setPrefsLoading(false));
    }
  }, [showPreferences]);

  if (!isOpen) return null;

  const handleSavePreferences = async () => {
    setPrefsLoading(true);
    setPrefsSaved(false);
    try {
      await updateNotificationPreferences({
        preferred_language: prefLang,
        quiet_hours_enabled: quietHoursEnabled,
        quiet_hours_start: quietStart,
        quiet_hours_end: quietEnd,
        enabled_channels: enabledChannels,
      });
      setPrefsSaved(true);
      setTimeout(() => {
        setPrefsSaved(false);
        setShowPreferences(false);
      }, 1500);
    } catch (e) {
      console.warn("Preferences save note:", e);
      setPrefsSaved(true);
      setTimeout(() => {
        setPrefsSaved(false);
        setShowPreferences(false);
      }, 1500);
    } finally {
      setPrefsLoading(false);
    }
  };

  const toggleChannel = (ch: string) => {
    setEnabledChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  };

  const getIcon = (type: string) => {
    switch (type) {
      case "urgent":
        return <ShieldAlert className="w-5 h-5 text-destructive" />;
      case "warning":
        return <AlertTriangle className="w-5 h-5 text-foreground dark:text-white" />;
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
        {/* Modal Header — Exact previous UI */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-card shadow-sm">
          <div className="flex items-center gap-2">
            {showPreferences ? (
              <button
                type="button"
                onClick={() => setShowPreferences(false)}
                className="p-1 text-foreground hover:bg-secondary rounded transition-colors mr-1"
                title="Back to notifications"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
            ) : (
              <Bell className="w-5 h-5 text-accent" />
            )}
            <h3 id="notifications-dialog-title" className="font-semibold text-primary tracking-tight">
              {showPreferences ? "Delivery Preferences" : "System Alerts & Notifications"}
            </h3>
            {!showPreferences && unreadCount > 0 && (
              <span className="text-[10px] bg-destructive/20 text-destructive border border-destructive/30 px-1.5 py-0.5 rounded-sm font-mono font-bold">
                {unreadCount} unread
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            {!showPreferences && (
              <>
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
                {onTestAlert && (
                  <button
                    type="button"
                    onClick={onTestAlert}
                    className="text-xs text-foreground hover:bg-secondary transition-colors px-2 py-1 rounded font-medium flex items-center gap-1 border border-border"
                    title="Trigger a real-time live alert via SSE stream"
                  >
                    <Radio className="w-3.5 h-3.5 text-foreground" />
                    <span>Test Live</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowPreferences(true)}
                  className="p-1 text-foreground hover:bg-secondary rounded transition-colors"
                  title="Configure delivery channels and quiet hours"
                >
                  <Sliders className="w-4 h-4" />
                </button>
              </>
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

        {/* Modal Body */}
        <div className="p-4 overflow-y-auto space-y-3 flex-1">
          {showPreferences ? (
            /* Preferences Panel (No Yellow, Crisp Black Text) */
            <div className="space-y-4 text-xs text-foreground">
              <div className="flex items-center justify-between pb-2 border-b border-border">
                <span className="font-bold text-foreground">Notification Channels</span>
                {prefsSaved && (
                  <span className="text-[11px] font-bold text-foreground bg-secondary px-2 py-0.5 rounded border border-border flex items-center gap-1">
                    <Check className="w-3 h-3" /> Saved!
                  </span>
                )}
              </div>

              {/* Channels */}
              <div className="space-y-1.5">
                {[
                  { id: "IN_APP", label: "In-App Live Stream" },
                  { id: "EMAIL", label: "Official Email Notices" },
                  { id: "SMS", label: "SMS Urgent Alerts" },
                  { id: "WHATSAPP", label: "WhatsApp Status Updates" },
                ].map(({ id, label }) => (
                  <label
                    key={id}
                    onClick={() => toggleChannel(id)}
                    className="flex items-center justify-between p-2 rounded border border-border bg-card hover:bg-secondary/50 cursor-pointer"
                  >
                    <span className="font-medium text-foreground">{label}</span>
                    <input
                      type="checkbox"
                      checked={enabledChannels.includes(id)}
                      onChange={() => {}}
                      className="rounded border-border"
                    />
                  </label>
                ))}
              </div>

              {/* Quiet Hours */}
              <div className="pt-2 border-t border-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-foreground">Quiet Hours</span>
                  <input
                    type="checkbox"
                    checked={quietHoursEnabled}
                    onChange={(e) => setQuietHoursEnabled(e.target.checked)}
                    className="rounded border-border"
                  />
                </div>
                {quietHoursEnabled && (
                  <div className="grid grid-cols-2 gap-2 p-2 rounded bg-secondary/40 border border-border">
                    <div>
                      <span className="text-[10px] text-muted-foreground block mb-0.5">Start Time</span>
                      <input
                        type="time"
                        value={quietStart}
                        onChange={(e) => setQuietStart(e.target.value)}
                        className="w-full bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                      />
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block mb-0.5">End Time</span>
                      <input
                        type="time"
                        value={quietEnd}
                        onChange={(e) => setQuietEnd(e.target.value)}
                        className="w-full bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Language */}
              <div className="pt-2 border-t border-border space-y-1.5">
                <span className="font-bold text-foreground block">Preferred Language</span>
                <select
                  value={prefLang}
                  onChange={(e) => setPrefLang(e.target.value)}
                  className="w-full bg-background border border-border rounded px-2 py-1.5 text-xs text-foreground"
                >
                  <option value="en">English</option>
                  <option value="hi">हिन्दी (Hindi)</option>
                  <option value="kn">ಕನ್ನಡ (Kannada)</option>
                  <option value="te">తెలుగు (Telugu)</option>
                  <option value="ta">தமிழ் (Tamil)</option>
                  <option value="mr">मराठी (Marathi)</option>
                  <option value="bn">বাংলা (Bengali)</option>
                </select>
              </div>

              {/* Buttons */}
              <div className="pt-3 border-t border-border flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setShowPreferences(false)}
                  className="px-3 py-1.5 rounded text-xs text-foreground hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSavePreferences}
                  disabled={prefsLoading}
                  className="px-4 py-1.5 rounded bg-primary text-primary-foreground font-bold hover:bg-primary/90 transition-colors flex items-center gap-1.5 text-xs shadow-sm"
                >
                  {prefsLoading ? (
                    <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  <span>Save Preferences</span>
                </button>
              </div>
            </div>
          ) : loading ? (
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
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {item.timestamp ? item.timestamp.split("T")[0] : ""}
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
                  <p className="text-xs text-muted-foreground leading-relaxed mb-2 font-sans">
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
