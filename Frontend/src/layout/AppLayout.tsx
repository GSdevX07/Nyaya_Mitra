import { useState, useEffect, useRef } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { Search, Bell, Activity, ChevronLeft, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { CommandPalette } from "@/components/CommandPalette";
import { NotificationsModal, type NotificationItem } from "@/components/NotificationsModal";
import { LawyerProfileModal } from "@/components/LawyerProfileModal";
import { fetchNotifications } from "@/lib/api";

const navItems = [
  { path: "/dashboard", label: "Command Center" },
  { path: "/cases", label: "Cases" },
  { path: "/radar", label: "Eligibility Radar" },
  { path: "/documents", label: "Documents" },
  { path: "/evidence", label: "Evidence" },
  { path: "/actions", label: "Actions" },
  { path: "/hearings", label: "Hearings" },
  { path: "/reports", label: "Reports" },
];

const DEFAULT_NOTIFICATIONS: NotificationItem[] = [
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
];

const READ_STORAGE_KEY = "nyaya_read_notification_ids";

function getReadIdsFromStorage(): string[] {
  try {
    return JSON.parse(localStorage.getItem(READ_STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveReadIdsToStorage(ids: string[]) {
  try {
    localStorage.setItem(READ_STORAGE_KEY, JSON.stringify(ids));
  } catch (err) {
    console.error("Failed to save read notification IDs:", err);
  }
}

export function AppLayout() {
  const location = useLocation();
  const [isHovered, setIsHovered] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  // Notification state
  const [notifications, setNotifications] = useState<NotificationItem[]>(() => {
    const readIds = getReadIdsFromStorage();
    return DEFAULT_NOTIFICATIONS.map((n) => ({
      ...n,
      read: readIds.includes(n.id),
    }));
  });
  const [notifLoading, setNotifLoading] = useState(false);

  // Nav horizontal scroll indicators
  const navRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = () => {
    if (navRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = navRef.current;
      setCanScrollLeft(scrollLeft > 5);
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 5);
    }
  };

  useEffect(() => {
    checkScroll();
    window.addEventListener("resize", checkScroll);
    return () => window.removeEventListener("resize", checkScroll);
  }, []);

  const scrollNav = (direction: "left" | "right") => {
    if (navRef.current) {
      const amount = direction === "left" ? -220 : 220;
      navRef.current.scrollBy({ left: amount, behavior: "smooth" });
    }
  };

  // Auto-scroll page to top on navigation
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    // Re-evaluate nav scroll buttons when route changes
    setTimeout(checkScroll, 100);
  }, [location.pathname]);

  // Fetch backend notifications on mount
  useEffect(() => {
    let isMounted = true;
    setNotifLoading(true);
    fetchNotifications()
      .then((data) => {
        if (!isMounted) return;
        const readIds = getReadIdsFromStorage();
        if (data && data.length > 0) {
          setNotifications(
            data.map((n: NotificationItem) => ({
              ...n,
              read: readIds.includes(n.id) || !!n.read,
            }))
          );
        } else {
          setNotifications(
            DEFAULT_NOTIFICATIONS.map((n) => ({
              ...n,
              read: readIds.includes(n.id),
            }))
          );
        }
      })
      .finally(() => {
        if (isMounted) setNotifLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleMarkAllRead = () => {
    setNotifications((prev) => {
      const updated = prev.map((n) => ({ ...n, read: true }));
      saveReadIdsToStorage(updated.map((n) => n.id));
      return updated;
    });
  };

  const handleMarkItemRead = (id: string) => {
    setNotifications((prev) => {
      const updated = prev.map((n) => (n.id === id ? { ...n, read: true } : n));
      const readIds = updated.filter((n) => n.read).map((n) => n.id);
      saveReadIdsToStorage(readIds);
      return updated;
    });
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-accent selection:text-accent-foreground relative overflow-x-hidden">
      {/* Subtle background grain/noise texture overlay */}
      <div className="pointer-events-none fixed inset-0 z-50 opacity-[0.03] mix-blend-overlay bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />

      {/* Global Top Navigation Bar (Full screen width) */}
      <header className="sticky top-0 z-40 w-full border-b border-white/10 bg-background/90 backdrop-blur-xl shadow-xl shadow-black/20">
        <div className="flex h-16 items-center px-4 md:px-8 w-full justify-between gap-2 md:gap-4">
          {/* Logo & Brand */}
          <Link
            to="/"
            className="flex items-center gap-2.5 mr-4 lg:mr-6 group hover:opacity-90 transition-opacity shrink-0"
          >
            <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-accent/10 border border-accent/20">
              <div className="absolute inset-0 bg-accent/20 rounded-lg animate-ping opacity-75" />
              <Activity className="w-5 h-5 text-accent relative z-10" />
            </div>
            <span className="font-bold text-lg tracking-tight text-white uppercase group-hover:text-accent transition-colors font-mono">
              Nyaya Mitra
            </span>
          </Link>

          {/* Navigation Links Container with Scroll Controls */}
          <div className="relative flex items-center flex-1 min-w-0 mx-1 md:mx-2">
            {canScrollLeft && (
              <button
                onClick={() => scrollNav("left")}
                className="absolute left-0 z-20 p-1.5 rounded-full bg-background/95 border border-white/20 text-accent hover:bg-white/10 shadow-lg backdrop-blur-md transition-all"
                title="Scroll left to see tabs"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}

            <nav
              ref={navRef}
              onScroll={checkScroll}
              className="flex items-center gap-1 md:gap-1.5 flex-1 overflow-x-auto no-scrollbar py-1 scroll-smooth"
            >
              {navItems.map((item) => {
                const isActive =
                  location.pathname === item.path ||
                  (item.path === "/cases" && location.pathname.startsWith("/case/")) ||
                  (item.path !== "/" && location.pathname.startsWith(item.path));

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`relative px-3 py-1.5 text-xs md:text-sm transition-all rounded-lg whitespace-nowrap shrink-0 font-medium ${
                      isActive
                        ? "text-white bg-white/10 font-semibold shadow-sm"
                        : "text-muted-foreground hover:text-white hover:bg-white/5"
                    }`}
                  >
                    {item.label}
                    {isActive && (
                      <motion.div
                        layoutId="nav-indicator"
                        className="absolute bottom-0 left-2 right-2 h-[2px] bg-accent rounded-t-full"
                        initial={false}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      />
                    )}
                  </Link>
                );
              })}
            </nav>

            {canScrollRight && (
              <button
                onClick={() => scrollNav("right")}
                className="absolute right-0 z-20 p-1.5 rounded-full bg-background/95 border border-white/20 text-accent hover:bg-white/10 shadow-lg backdrop-blur-md transition-all animate-pulse"
                title="More tabs available Click to scroll right"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Controls & Profile */}
          <div className="flex items-center gap-2 md:gap-3 ml-2 shrink-0">
            <button
              onClick={() => setIsSearchOpen(true)}
              className="p-2 text-muted-foreground hover:text-white hover:bg-white/10 rounded-xl transition-colors flex items-center gap-1.5"
              title="Search cases & actions (Ctrl+K)"
            >
              <Search className="w-4 h-4 md:w-5 md:h-5 text-accent" />
              <span className="text-[10px] hidden lg:inline-block border border-white/10 px-1.5 py-0.5 rounded text-muted-foreground font-mono">
                ⌘K
              </span>
            </button>

            <button
              onClick={() => setIsNotificationsOpen(true)}
              className="p-2 text-muted-foreground hover:text-white hover:bg-white/10 rounded-xl transition-colors relative"
              title="System Alerts"
            >
              <Bell className="w-4 h-4 md:w-5 md:h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive rounded-full animate-pulse" />
              )}
            </button>

            <div className="w-px h-5 bg-white/10 mx-1" />

            <button
              onClick={() => setIsProfileOpen(true)}
              className="flex items-center gap-2 text-xs md:text-sm text-muted-foreground hover:text-white p-1.5 rounded-xl hover:bg-white/10 transition-all cursor-pointer"
              title="View Lawyer Profile & Credentials"
            >
              <div className="w-7 h-7 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center text-accent font-semibold text-xs font-mono">
                RS
              </div>
              <span className="hidden md:inline font-medium text-white/90">
                Legal Officer 104
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area (Full screen width) */}
      <main className="flex-1 relative z-10 w-full">
        <Outlet />
      </main>

      {/* Global AI Intelligence Floating Circular Icon / Expanded Panel (Bottom Right) */}
      <div className="fixed bottom-6 right-6 z-40">
        <motion.div
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className="bg-background/95 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/80 overflow-hidden cursor-pointer flex flex-col"
          initial={false}
          animate={{
            width: isHovered ? 320 : 48,
            height: isHovered ? 160 : 48,
            borderRadius: isHovered ? 16 : 9999,
          }}
          transition={{ type: "spring", stiffness: 350, damping: 25 }}
        >
          <AnimatePresence mode="wait">
            {!isHovered ? (
              <motion.div
                key="collapsed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="w-12 h-12 flex items-center justify-center relative"
              >
                <Activity className="w-5 h-5 text-accent animate-pulse" />
                <span className="absolute top-2 right-2 w-2 h-2 bg-accent rounded-full animate-ping opacity-75" />
              </motion.div>
            ) : (
              <motion.div
                key="expanded"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="p-4 w-80"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="w-4 h-4 text-accent animate-pulse" />
                  <span className="text-xs font-semibold text-accent uppercase tracking-wider">
                    Nyaya Intelligence Engine
                  </span>
                </div>
                <ul className="space-y-2 text-xs text-muted-foreground">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-white/20 animate-pulse" />
                    Monitoring Undertrial Prisoner Records
                  </li>
                  <li className="flex items-center gap-2 text-emerald-400">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    Section 479 BNSS Rule Engine Active
                  </li>
                  <li className="flex items-center gap-2 text-amber-400">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                    Parent Contact Verification Ready
                  </li>
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      <CommandPalette isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
      <NotificationsModal
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        notifications={notifications}
        onMarkAllRead={handleMarkAllRead}
        onMarkItemRead={handleMarkItemRead}
        loading={notifLoading}
      />
      <LawyerProfileModal isOpen={isProfileOpen} onClose={() => setIsProfileOpen(false)} />
    </div>
  );
}


