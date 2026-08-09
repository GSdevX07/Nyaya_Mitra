import { useState, useEffect } from "react";
import { BarChart3, TrendingUp, Users, Shield, Clock, Award, PieChart } from "lucide-react";
import { fetchReports } from "@/lib/api";

interface ReportsData {
  overview: {
    total_undertrials_monitored: number;
    bnss_479_eligible: number;
    senior_citizens: number;
    medical_priority_cases: number;
    average_custody_days: number;
    estimated_hours_saved_by_ai: number;
  };
  court_jurisdiction_breakdown: { jail: string; count: number }[];
  eligibility_distribution: { category: string; count: number }[];
}

export function ReportsPage() {
  const [data, setData] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const res = await fetchReports();
      if (res) {
        setData(res);
      } else {
        // Fallback stats
        setData({
          overview: {
            total_undertrials_monitored: 5,
            bnss_479_eligible: 3,
            senior_citizens: 2,
            medical_priority_cases: 2,
            average_custody_days: 436.0,
            estimated_hours_saved_by_ai: 340,
          },
          court_jurisdiction_breakdown: [
            { jail: "District Jail, synthetic", count: 2 },
            { jail: "Central Jail, synthetic", count: 2 },
            { jail: "Sub-Jail, synthetic", count: 1 },
          ],
          eligibility_distribution: [
            { category: "Eligible & Complete", count: 3 },
            { category: "Missing Documents", count: 1 },
            { category: "Ineligible (Sentence Threshold)", count: 1 },
          ],
        });
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading || !data) {
    return (
      <div className="p-16 text-center text-muted-foreground animate-pulse">
        Compiling legal analytics report from Nyaya Mitra pipeline...
      </div>
    );
  }

  const { overview, court_jurisdiction_breakdown, eligibility_distribution } = data;

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Legal Operations Intelligence
            </span>
            <span className="text-xs text-muted-foreground font-mono">System Analytics & DLSA Impact</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Legal Analytics & Population Reports</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Impact metrics covering Section 479 BNSS relief, detention reduction, and DLSA legal aid speedup.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs">Total Undertrials</span>
            <Users className="w-4 h-4 text-accent" />
          </div>
          <div className="text-3xl font-bold text-white">{overview.total_undertrials_monitored}</div>
          <div className="text-xs text-emerald-400 font-medium flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> 100% Synthetic Monitored
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs">BNSS 479 Eligible</span>
            <Shield className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-white">{overview.bnss_479_eligible}</div>
          <div className="text-xs text-muted-foreground">
            {Math.round((overview.bnss_479_eligible / overview.total_undertrials_monitored) * 100)}% ready for bail motion
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs">Avg Custody Duration</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-bold text-white">{overview.average_custody_days} <span className="text-sm font-normal text-muted-foreground">days</span></div>
          <div className="text-xs text-muted-foreground">Across all facilities</div>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs">Legal Time Saved</span>
            <Award className="w-4 h-4 text-accent" />
          </div>
          <div className="text-3xl font-bold text-white">{overview.estimated_hours_saved_by_ai} <span className="text-sm font-normal text-muted-foreground">hrs</span></div>
          <div className="text-xs text-accent font-medium">Automated petition drafting</div>
        </div>
      </div>

      {/* Analytics Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Facility Breakdown */}
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-4 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-accent" />
            <h3 className="text-base font-semibold text-white">Facility Inmate Breakdown</h3>
          </div>
          <div className="space-y-3">
            {court_jurisdiction_breakdown.map(item => (
              <div key={item.jail} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-white font-medium">{item.jail}</span>
                  <span className="text-muted-foreground">{item.count} cases</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full"
                    style={{
                      width: `${(item.count / overview.total_undertrials_monitored) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Card 2: Eligibility Category Distribution */}
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-4 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <PieChart className="w-5 h-5 text-accent" />
            <h3 className="text-base font-semibold text-white">Eligibility Status Breakdown</h3>
          </div>
          <div className="space-y-3">
            {eligibility_distribution.map(item => (
              <div key={item.category} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-white font-medium">{item.category}</span>
                  <span className="text-muted-foreground">{item.count} cases</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{
                      width: `${(item.count / overview.total_undertrials_monitored) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
