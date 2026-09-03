import { useState, useEffect, useRef, useMemo } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Search, Bell, Activity, ChevronLeft, ChevronRight, LogOut } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { CommandPalette } from "@/components/CommandPalette";
import { NotificationsModal, type NotificationItem } from "@/components/NotificationsModal";
import { LawyerProfileModal } from "@/components/LawyerProfileModal";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { fetchNotifications } from "@/lib/api";
import { useAuth, type Role } from "@/lib/auth";

interface NavItem {
  path: string;
  label: string;
}

function getNavItemsForRole(role?: Role): NavItem[] {
  switch (role) {
    case "ACCUSED_USER":
      return [{ path: "/my-case", label: "My Legal Status" }];

    case "FAMILY_GUARDIAN":
      return [{ path: "/family/status", label: "Family Assistance Portal" }];

    case "READ_ONLY_AUDITOR":
      return [
        { path: "/audit", label: "Audit Ledger" },
        { path: "/legal-sources", label: "Legal Knowledge Audit" },
        { path: "/reports", label: "Reports" },
        { path: "/evidence", label: "Evidence Integrity" },
      ];

    case "DEFENSE_ADVOCATE":
      return [
        { path: "/advocate", label: "My Assigned Cases" },
        { path: "/radar", label: "Eligibility Radar" },
        { path: "/documents", label: "Assigned Documents" },
        { path: "/legal-sources", label: "Legal Knowledge Base" },
        { path: "/actions", label: "Counsel Actions" },
        { path: "/hearings", label: "Hearings" },
      ];

    case "CONTROLLED_EXTERNAL_ADVOCATE":
      return [
        { path: "/advocate", label: "My Assigned Cases" },
        { path: "/documents", label: "Authorized Documents" },
        { path: "/legal-sources", label: "Legal Knowledge Base" },
        { path: "/hearings", label: "Hearings" },
      ];

    case "JAIL_OFFICER":
      return [
        { path: "/jail", label: "Custody Desk" },
        { path: "/cases", label: "Inmate Roll" },
        { path: "/documents", label: "Intake Documents" },
        { path: "/hearings", label: "Hearings" },
        { path: "/reports", label: "Reports" },
      ];

    case "POLICE_OFFICER":
      return [
        { path: "/police", label: "Police Records Desk" },
        { path: "/hearings", label: "Court Production Schedule" },
      ];

    case "PLATFORM_ADMIN":
      return [
        { path: "/admin", label: "Admin Console" },
        { path: "/ingestion", label: "Data Ingestion" },
        { path: "/audit", label: "Audit Logs" },
        { path: "/reports", label: "Reports" },
      ];

    case "GOV_ADMIN":
      return [
        { path: "/gov", label: "State Overview" },
        { path: "/dashboard", label: "Command Center" },
        { path: "/cases", label: "Cases" },
        { path: "/identity-review", label: "Identity Review" },
        { path: "/legal-sources", label: "Legal Knowledge Governance" },
        { path: "/reports", label: "Reports" },
        { path: "/audit", label: "Audit" },
      ];

    case "SUPERVISING_LEGAL_OFFICER":
      return [
        { path: "/dashboard", label: "Command Center" },
        { path: "/cases", label: "Cases" },
        { path: "/identity-review", label: "Identity Review" },
        { path: "/radar", label: "Eligibility Radar" },
        { path: "/documents", label: "Documents" },
        { path: "/evidence", label: "Evidence" },
        { path: "/actions", label: "Actions" },
        { path: "/hearings", label: "Hearings" },
        { path: "/legal-sources", label: "Legal Knowledge Governance" },
        { path: "/ingestion", label: "Data Ingestion" },
        { path: "/audit", label: "Audit" },
        { path: "/reports", label: "Reports" },
      ];

    case "DLSA_OFFICER":
    default:
      return [
        { path: "/dashboard", label: "Command Center" },
        { path: "/cases", label: "Cases" },
        { path: "/identity-review", label: "Identity Review" },
        { path: "/radar", label: "Eligibility Radar" },
        { path: "/documents", label: "Documents" },
        { path: "/evidence", label: "Evidence" },
        { path: "/actions", label: "Actions" },
        { path: "/hearings", label: "Hearings" },
        { path: "/legal-sources", label: "Legal Knowledge" },
        { path: "/ingestion", label: "Data Ingestion" },
        { path: "/reports", label: "Reports" },
      ];
  }
}



function getDefaultNotificationsForRole(role?: string): NotificationItem[] {
  switch (role) {
    case "POLICE_OFFICER":
      return [
        {
          id: "DEF-POLICE-1",
          title: "Remand Period Expiry Alert — Sec 187 BNSS",
          message: "Accused Suresh Kumar (FIR 204/2026, Crime Branch Delhi) initial 15-day police custody remand expires in 48 hours.",
          timestamp: "Just now",
          type: "urgent",
          case_id: "UTP-0001",
        },
        {
          id: "DEF-POLICE-2",
          title: "Pending Investigation Charge Sheet Deadline",
          message: "Charge Sheet for Case UTP-0015 (FIR 88/2026) due within 14 days under Section 193 BNSS.",
          timestamp: "2 hrs ago",
          type: "warning",
          case_id: "UTP-0015",
        },
      ];

    case "JAIL_OFFICER":
      return [
        {
          id: "DEF-JAIL-1",
          title: "Section 479(2) BNSS Mandatory Bail Application Required",
          message: "Undertrial prisoner Ramesh Kumar (UTP-0007) has completed 1/3rd sentence duration. Superintendent application to Court required forthwith.",
          timestamp: "Just now",
          type: "urgent",
          case_id: "UTP-0007",
        },
        {
          id: "DEF-JAIL-2",
          title: "Nominal Roll & Custody Certificate Due",
          message: "High Court Registry requested verified Nominal Roll and custody conduct certificate for Suresh Kumar (UTP-0001).",
          timestamp: "1 hr ago",
          type: "warning",
          case_id: "UTP-0001",
        },
      ];

    case "DEFENSE_ADVOCATE":
    case "CONTROLLED_EXTERNAL_ADVOCATE":
      return [
        {
          id: "DEF-ADV-1",
          title: "Bail Application Draft Ready for Filing",
          message: "Consolidated BNSS Section 479 application package for Suresh Kumar (UTP-0001) generated and verified against 2024 Supreme Court SOP.",
          timestamp: "10 mins ago",
          type: "success",
          case_id: "UTP-0001",
        },
        {
          id: "DEF-ADV-2",
          title: "Client Eligibility Radar Alert",
          message: "New Section 479(1) Proviso 1 eligibility detected for Ramesh Kumar (UTP-0007, First-time offender threshold reached).",
          timestamp: "45 mins ago",
          type: "urgent",
          case_id: "UTP-0007",
        },
      ];

    case "DLSA_OFFICER":
      return [
        {
          id: "DEF-DLSA-1",
          title: "Legal Aid Panel Assignment Pending",
          message: "Indigent undertrial prisoner (UTP-0015) has requested DLSA representation. Panel advocate assignment awaiting endorsement.",
          timestamp: "20 mins ago",
          type: "warning",
          case_id: "UTP-0015",
        },
        {
          id: "DEF-DLSA-2",
          title: "High Priority Bail Eligibility Flagged",
          message: "Alert [HIGH]: Case UTP-0007 (Ramesh Kumar) is legally eligible for bail under BNSS 479. Urgency Score: 266.",
          timestamp: "1 hr ago",
          type: "urgent",
          case_id: "UTP-0007",
        },
      ];

    case "SUPERVISING_LEGAL_OFFICER":
    case "GOV_ADMIN":
      return [
        {
          id: "DEF-SLSA-1",
          title: "Statutory Citation Integrity Escalation",
          message: "Unsupported legal claims detected in advocate filing draft. Routed to Supervising Legal Officer for human verification.",
          timestamp: "15 mins ago",
          type: "urgent",
          case_id: "UTP-0001",
        },
        {
          id: "DEF-SLSA-2",
          title: "Discovered Legal Source Pending Approval",
          message: "New statutory enactment proposed by DLSA Officer is in 'discovered' state awaiting formal supervisor review.",
          timestamp: "3 hrs ago",
          type: "warning",
          case_id: "src_bnss_2023",
        },
      ];

    case "READ_ONLY_AUDITOR":
      return [
        {
          id: "DEF-AUDIT-1",
          title: "Statutory Compliance Audit Alert",
          message: "Discrepancy detected in custody days computation between Police FIR arrest log and Prison intake register for UTP-0015.",
          timestamp: "30 mins ago",
          type: "warning",
          case_id: "UTP-0015",
        },
      ];

    case "ACCUSED_USER":
    case "FAMILY_GUARDIAN":
      return [
        {
          id: "DEF-CITIZEN-1",
          title: "Bail Application Status Update",
          message: "Your legal aid counsel has submitted an application for bail under Section 479 BNSS. Hearing date set for 2026-09-08.",
          timestamp: "1 hr ago",
          type: "success",
          case_id: "UTP-0001",
        },
        {
          id: "DEF-CITIZEN-2",
          title: "Assigned Legal Aid Advocate Contact",
          message: "Adv. Rajesh Sharma (DLSA Panel) has been designated as your defense advocate.",
          timestamp: "Yesterday",
          type: "info",
          case_id: "UTP-0001",
        },
      ];

    case "PLATFORM_ADMIN":
    default:
      return [
        {
          id: "DEF-ADMIN-1",
          title: "Database Sync & Health Check",
          message: "PostgreSQL dual-write adapter active. SQLite primary replica synchronized.",
          timestamp: "5 mins ago",
          type: "info",
        },
      ];
  }
}


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
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [isHovered, setIsHovered] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const navItems = useMemo(() => getNavItemsForRole(user?.role), [user?.role]);

  // Notification state
  const [notifications, setNotifications] = useState<NotificationItem[]>(() => {
    const readIds = getReadIdsFromStorage();
    return getDefaultNotificationsForRole(user?.role).map((n) => ({
      ...n,
      read: readIds.includes(n.id),
    }));
  });

  const [notifLoading, setNotifLoading] = useState(false);

  const [isNavHovered, setIsNavHovered] = useState(false);

  // Nav horizontal scroll indicators
  const navRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [isScrollable, setIsScrollable] = useState(false);

  const checkScroll = () => {
    if (navRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = navRef.current;
      setCanScrollLeft(scrollLeft > 5);
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 5);
      setIsScrollable(scrollWidth > clientWidth + 5);
    }
  };

  const handleNavWheel = (e: React.WheelEvent) => {
    if (navRef.current && isScrollable) {
      if (Math.abs(e.deltaX) > 0) return;
      navRef.current.scrollBy({ left: e.deltaY * 1.5, behavior: "auto" });
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
            getDefaultNotificationsForRole(user?.role).map((n) => ({
              ...n,
              read: readIds.includes(n.id),
            }))
          );
        }
      })
      .catch((err) => {
        console.warn("Could not load backend notifications, falling back to role defaults:", err);
        if (!isMounted) return;
        const readIds = getReadIdsFromStorage();
        setNotifications(
          getDefaultNotificationsForRole(user?.role).map((n) => ({
            ...n,
            read: readIds.includes(n.id),
          }))
        );
      })
      .finally(() => {
        if (isMounted) setNotifLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [user?.role, user?.id]);


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
      <header className="sticky top-0 z-40 w-full border-b-2 border-border bg-card shadow-sm">
        {/* Top Environment & Institutional Positioning Banner */}
        <div className="bg-primary/10 border-b border-border/60 px-4 md:px-8 py-1 flex items-center justify-between text-[11px] font-mono">
          <div className="flex items-center gap-2 text-foreground/80">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold text-foreground">DEMO / SYNTHETIC ENVIRONMENT</span>
            <span className="text-muted-foreground">• Institutional Operations Platform</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground hidden sm:inline">
              Section 479 BNSS Rule Engine v1 (2023)
            </span>
            <span className="px-2 py-0.5 rounded bg-primary/20 text-primary font-bold text-[10px]">
              PROPOSED INSTITUTIONAL DEPLOYMENT
            </span>
          </div>
        </div>

        <div className="flex h-16 items-center px-4 md:px-8 w-full justify-between gap-2 md:gap-4">
          {/* Logo & Brand */}
          <Link
            to="/"
            className="flex items-center gap-2.5 mr-4 lg:mr-6 group hover:opacity-90 transition-opacity shrink-0"
          >
            <div className="relative flex items-center justify-center w-8 h-8 rounded-sm bg-primary text-primary-foreground font-serif font-black">
              <Activity className="w-5 h-5 text-primary-foreground relative z-10" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg tracking-tight text-foreground uppercase group-hover:text-muted-foreground transition-colors font-serif leading-none">
                Nyaya Mitra
              </span>
              <span className="text-[9px] font-mono text-muted-foreground tracking-wider uppercase">
                Legal Operations
              </span>
            </div>
          </Link>

          {/* Navigation Links Container with Hover Scroll Controls */}
          <div
            className="relative flex items-center flex-1 min-w-0 mx-1 md:mx-2"
            onMouseEnter={() => {
              setIsNavHovered(true);
              checkScroll();
            }}
            onMouseLeave={() => setIsNavHovered(false)}
          >
            {isScrollable && (canScrollLeft || isNavHovered) && (
              <button
                onClick={() => scrollNav("left")}
                className={`absolute left-0 z-20 p-1.5 rounded-sm bg-card/95 backdrop-blur-md border border-border text-foreground hover:bg-primary hover:text-primary-foreground shadow-lg transition-all duration-200 flex items-center justify-center ${
                  !canScrollLeft ? "opacity-50 cursor-not-allowed" : "opacity-100 hover:scale-105"
                }`}
                title="Scroll left to see tabs"
                disabled={!canScrollLeft}
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}

            <nav
              ref={navRef}
              onScroll={checkScroll}
              onWheel={handleNavWheel}
              className="flex items-center gap-1 md:gap-1.5 flex-1 overflow-x-auto no-scrollbar py-1 scroll-smooth px-1"
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
                    className={`relative px-3.5 py-1.5 text-xs md:text-sm transition-all rounded-sm whitespace-nowrap shrink-0 font-serif ${
                      isActive
                        ? "text-primary-foreground bg-primary font-bold shadow-sm"
                        : "text-foreground/80 hover:text-foreground hover:bg-secondary font-semibold"
                    }`}
                  >
                    {item.label}
                    {isActive && (
                      <motion.div
                        layoutId="nav-indicator"
                        className="absolute bottom-0 left-2 right-2 h-[2.5px] bg-primary-foreground rounded-t-full"
                        initial={false}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      />
                    )}
                  </Link>
                );
              })}
            </nav>

            {isScrollable && (canScrollRight || isNavHovered) && (
              <button
                onClick={() => scrollNav("right")}
                className={`absolute right-0 z-20 p-1.5 rounded-sm bg-card/95 backdrop-blur-md border border-border text-foreground hover:bg-primary hover:text-primary-foreground shadow-lg transition-all duration-200 flex items-center justify-center ${
                  !canScrollRight ? "opacity-50 cursor-not-allowed" : "opacity-100 hover:scale-105"
                }`}
                title="Scroll right to see tabs"
                disabled={!canScrollRight}
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Controls & Profile */}
          <div className="flex items-center gap-2 md:gap-3 ml-2 shrink-0">
            <button
              onClick={() => setIsSearchOpen(true)}
              className="p-2 text-foreground hover:bg-secondary border border-border rounded-sm transition-colors flex items-center gap-1.5"
              title="Search cases & actions (Ctrl+K)"
            >
              <Search className="w-4 h-4 md:w-5 md:h-5 text-foreground" />
              <span className="text-[10px] hidden lg:inline-block border border-border bg-input px-1.5 py-0.5 rounded-sm text-foreground font-mono font-bold">
                ⌘K
              </span>
            </button>

            <button
              onClick={() => setIsNotificationsOpen(true)}
              className="p-2 text-foreground hover:bg-secondary border border-border rounded-sm transition-colors relative"
              title="System Alerts"
            >
              <Bell className="w-4 h-4 md:w-5 md:h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-destructive rounded-full animate-pulse border border-card" />
              )}
            </button>

            <div className="w-px h-6 bg-border mx-1" />

            <button
              onClick={() => setIsProfileOpen(true)}
              className="flex items-center gap-2 text-xs md:text-sm text-foreground p-1.5 rounded-sm border border-border hover:bg-secondary transition-all cursor-pointer"
              title="View User Profile & Security Credentials"
            >
              <div className="w-7 h-7 rounded-sm bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs font-mono">
                {(user?.full_name || user?.role || "NM")
                  .split(" ")
                  .map((w: string) => w[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase()}
              </div>
              <div className="hidden md:flex flex-col text-left">
                <span className="font-bold font-serif text-foreground text-xs leading-none">
                  {user?.full_name || "Institutional User"}
                </span>
                <span className="text-[10px] font-mono text-primary font-bold leading-tight mt-0.5">
                  [{user?.role || "OFFICER"}]
                </span>
              </div>
            </button>

            <button
              onClick={async () => {
                await logout();
                navigate("/login", { replace: true });
              }}
              className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 border border-border rounded-sm transition-colors"
              title="Sign Out Session"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area (Full screen width) */}
      <main className="flex-1 w-full" role="main" aria-label="Main Application Content">
        <ErrorBoundary fallbackTitle="Workspace Section Error">
          <Outlet />
        </ErrorBoundary>
      </main>


      {/* Global AI Intelligence Floating Circular Icon / Expanded Panel (Bottom Right) */}
      <div className="fixed bottom-6 right-6 z-40">
        <motion.div
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className="bg-background/95 backdrop-blur-xl border border-border shadow-2xl shadow-primary/5 overflow-hidden cursor-pointer flex flex-col"
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
                <span className="absolute top-2 right-2 w-2 h-2 bg-accent rounded-sm animate-ping opacity-75" />
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
                    <div className="w-1.5 h-1.5 rounded-sm bg-muted animate-pulse" />
                    Monitoring Undertrial Prisoner Records
                  </li>
                  <li className="flex items-center gap-2 text-foreground">
                    <div className="w-1.5 h-1.5 rounded-sm bg-accent" />
                    Section 479 BNSS Rule Engine Active
                  </li>
                  <li className="flex items-center gap-2 text-muted-foreground">
                    <div className="w-1.5 h-1.5 rounded-sm bg-muted-foreground" />
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


