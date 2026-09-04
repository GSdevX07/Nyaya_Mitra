/**
 * auth.tsx — Production Auth Service & Context for Nyaya Mitra Frontend
 *
 * Security Model:
 *  - Short-lived JWT Access Token is kept strictly in React Memory (State).
 *  - Refresh Token is held in sessionStorage (cleared upon tab close).
 *  - No sensitive credentials or master keys in localStorage.
 *  - Automatic Bearer token header injection on all backend calls.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const REFRESH_TOKEN_KEY = "nyaya_refresh_token";

import { type Capability, type PermissionContext, checkPermission } from "./permissions";

export type Role =
  | "PLATFORM_ADMIN"
  | "GOV_ADMIN"
  | "JAIL_OFFICER"
  | "POLICE_OFFICER"
  | "DLSA_OFFICER"
  | "SUPERVISING_LEGAL_OFFICER"
  | "DEFENSE_ADVOCATE"
  | "CONTROLLED_EXTERNAL_ADVOCATE"
  | "ACCUSED_USER"
  | "FAMILY_GUARDIAN"
  | "READ_ONLY_AUDITOR"
  | "INTEGRATION_SERVICE";

export interface UserProfile {
  id: string;
  email: string;
  role: Role;
  full_name: string;
  org_id: string;
  district?: string;
  state_id?: string;
  state?: string;
  scope_type?: string;
  authorized_district_ids?: string[];
  facility_ids?: string[];
  linked_case_id?: string;
  police_station?: string;
  police_station_id?: string;
  jurisdiction_ids?: string[];
}

export interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<Role>;
  loginWithDemoRole: (role: Role) => Promise<Role>;
  logout: () => Promise<void>;
  hasRole: (...roles: Role[]) => boolean;
  can: (capability: Capability, context?: PermissionContext) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

let _inMemoryAccessToken: string | null = null;

function parseJwt(token: string): any {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return {};
  }
}

export function getAuthToken(): string | null {
  return _inMemoryAccessToken;
}

export function getAuthHeaders(): HeadersInit {
  if (_inMemoryAccessToken) {
    return {
      Authorization: `Bearer ${_inMemoryAccessToken}`,
      "Content-Type": "application/json",
    };
  }
  return {
    "Content-Type": "application/json",
  };
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const updateSession = (accessToken: string, userProfile: UserProfile, refreshToken?: string) => {
    _inMemoryAccessToken = accessToken;
    setToken(accessToken);
    const jwtClaims = parseJwt(accessToken);
    const enrichedUser: UserProfile = {
      ...userProfile,
      district: jwtClaims.district || userProfile.district,
      state_id: jwtClaims.state_id || userProfile.state_id,
      state: jwtClaims.state || userProfile.state,
      scope_type: jwtClaims.scope_type || userProfile.scope_type,
      authorized_district_ids: jwtClaims.authorized_district_ids || userProfile.authorized_district_ids,
      facility_ids: jwtClaims.facility_ids || userProfile.facility_ids,
      linked_case_id: jwtClaims.linked_case_id || userProfile.linked_case_id,
      police_station: jwtClaims.police_station || userProfile.police_station,
      police_station_id: jwtClaims.police_station_id || userProfile.police_station_id,
      jurisdiction_ids: jwtClaims.jurisdiction_ids || userProfile.jurisdiction_ids,
    };
    setUser(enrichedUser);
    if (refreshToken) {
      sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  };

  const clearSession = () => {
    _inMemoryAccessToken = null;
    setToken(null);
    setUser(null);
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  };

  // Attempt silent token refresh on app mount if a refresh token exists in sessionStorage
  const attemptSilentRefresh = useCallback(async () => {
    const storedRefresh = sessionStorage.getItem(REFRESH_TOKEN_KEY);
    if (!storedRefresh) {
      setIsLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: storedRefresh }),
      });

      if (res.ok) {
        const data = await res.json();
        updateSession(
          data.access_token,
          {
            id: data.user_id,
            email: "",
            role: data.role as Role,
            full_name: data.full_name,
            org_id: data.org_id,
          },
          data.refresh_token
        );
      } else {
        clearSession();
      }
    } catch {
      clearSession();
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    attemptSilentRefresh();
  }, [attemptSilentRefresh]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Login failed with status ${res.status}`);
      }

      const data = await res.json();
      updateSession(
        data.access_token,
        {
          id: data.user_id,
          email: email.toLowerCase(),
          role: data.role as Role,
          full_name: data.full_name,
          org_id: data.org_id,
        },
        data.refresh_token
      );
      return data.role as Role;
    } finally {

      setIsLoading(false);
    }
  };



  const loginWithDemoRole = async (role: Role) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/demo-token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Demo login failed with status ${res.status}`);
      }

      const data = await res.json();
      updateSession(
        data.access_token,
        {
          id: data.user_id,
          email: `${role.toLowerCase()}@demo.nyayamitra.in`,
          role: data.role as Role,
          full_name: data.full_name,
          org_id: data.org_id,
        },
        data.refresh_token
      );
      return role;
    } finally {
      setIsLoading(false);
    }
  };


  const logout = async () => {
    if (_inMemoryAccessToken) {
      try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: "POST",
          headers: getAuthHeaders(),
        });
      } catch (err) {
        console.warn("Logout notification error:", err);
      }
    }
    clearSession();
  };

  const hasRole = (...roles: Role[]) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const can = (capability: Capability, context?: PermissionContext): boolean => {
    return checkPermission(user, capability, context);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        loginWithDemoRole,
        logout,
        hasRole,
        can,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
