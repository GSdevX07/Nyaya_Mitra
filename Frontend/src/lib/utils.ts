import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatRoleTitle(role?: string): string {
  if (!role) return "Legal Officer";
  const r = role.toUpperCase();
  if (r.includes("DEFENSE_ADVOCATE") || r === "ADVOCATE") return "Defense Panel Counsel";
  if (r.includes("CONTROLLED_EXTERNAL_ADVOCATE")) return "Panel Advocate";
  if (r.includes("DLSA_OFFICER") || r === "DLSA") return "DLSA Legal Aid Officer";
  if (r.includes("SUPERVISING_LEGAL_OFFICER") || r.includes("SUPERVISOR")) return "Supervising Legal Officer";
  if (r.includes("JAIL_OFFICER") || r.includes("PRISON")) return "Jail Custody Officer";
  if (r.includes("POLICE_OFFICER") || r.includes("POLICE")) return "Police Records Officer";
  if (r.includes("PLATFORM_ADMIN")) return "Platform Administrator";
  if (r.includes("GOV_ADMIN")) return "State Legal Authority (SLSA)";
  if (r.includes("READ_ONLY_AUDITOR")) return "Statutory Auditor";
  return role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export interface ActorInfo {
  name?: string;
  role?: string;
  district?: string;
  jail?: string;
  station?: string;
  location?: string;
}

export function formatCaseActor(actor?: ActorInfo): string {
  const name = (actor?.name || "").trim();
  const rawRole = actor?.role || "";
  const roleTitle = formatRoleTitle(rawRole);

  // Pick location prioritizing specific institution (jail/police station) for respective roles
  let loc = (actor?.location || "").trim();
  if (!loc) {
    if (rawRole.toUpperCase().includes("JAIL") && actor?.jail) {
      loc = actor.jail.trim();
    } else if (rawRole.toUpperCase().includes("POLICE") && actor?.station) {
      loc = actor.station.trim();
    } else if (actor?.district) {
      loc = actor.district.trim();
    } else if (actor?.jail) {
      loc = actor.jail.trim();
    } else if (actor?.station) {
      loc = actor.station.trim();
    }
  }

  const isGenericName =
    !name ||
    name.toLowerCase().includes("unknown") ||
    name.toLowerCase().includes("demo") ||
    name.toLowerCase() === "user" ||
    name.toLowerCase() === "actor";

  if (!isGenericName) {
    if (roleTitle && loc) {
      return `${name} (${roleTitle}, ${loc})`;
    }
    if (roleTitle) {
      return `${name} (${roleTitle})`;
    }
    if (loc) {
      return `${name} (${loc})`;
    }
    return name;
  }

  // When name is not available or is generic, display exact Role + Location/Facility
  if (roleTitle && loc) {
    return `${roleTitle} (${loc})`;
  }
  if (roleTitle) {
    return roleTitle;
  }
  if (loc) {
    return `Legal Officer (${loc})`;
  }
  return "Authorized Legal Officer";
}

export function resolveCaseUpdater(
  errDetail?: any,
  caseRecord?: any,
  fallbackDistrict?: string
): string {
  const c = caseRecord?.case || caseRecord || {};
  const detail = typeof errDetail === "object" ? errDetail : {};

  const name =
    detail.last_modified_by ||
    c.last_modified_by ||
    "";

  const role =
    detail.last_modified_role ||
    c.last_modified_role ||
    "";

  const district =
    detail.last_modified_district ||
    c.last_modified_district ||
    c.district ||
    fallbackDistrict ||
    "";

  const jail =
    detail.last_modified_jail ||
    c.last_modified_jail ||
    c.jail_location ||
    "";

  const station =
    detail.last_modified_station ||
    c.last_modified_station ||
    c.police_station ||
    "";

  // Check latest timeline event if name or role is still missing
  let finalName = name;
  let finalRole = role;
  if ((!finalName || !finalRole) && Array.isArray(c.timeline) && c.timeline.length > 0) {
    const latest = c.timeline[c.timeline.length - 1];
    if (!finalName && latest.actor) finalName = latest.actor;
    if (!finalRole && latest.actor_role) finalRole = latest.actor_role;
  }

  // Check assigned lawyer if still missing
  if (!finalName && c.assigned_lawyer) {
    finalName = c.assigned_lawyer;
    if (!finalRole) finalRole = "DEFENSE_ADVOCATE";
  }

  return formatCaseActor({
    name: finalName,
    role: finalRole,
    district,
    jail,
    station,
  });
}
