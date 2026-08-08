export type CaseStatus = "DISCOVERED" | "VERIFIED" | "DOCUMENTS_PENDING" | "ELIGIBILITY_CALCULATED" | "LEGAL_REVIEW" | "FILED" | "HEARING" | "RESOLVED";

export interface DocumentInfo {
  id: string;
  name: string;
  type: "Remand Order" | "Charge Sheet" | "Custody Record" | "Previous Bail Order" | "Latest Hearing Order" | "Identity Record";
  status: "available" | "missing" | "processing";
}

export interface EvidenceNode {
  id: string;
  type: "FACT" | "DOCUMENT" | "EXTRACTION" | "CALCULATION" | "LEGAL_SOURCE" | "CONCLUSION";
  title: string;
  description: string;
  confidence?: number;
  sourceDocId?: string;
}

export interface LegalSource {
  id: string;
  section: string;
  relevance: number;
  passage: string;
  reasoning: string;
}

export interface Case {
  id: string;
  prisonerName: string;
  age: number;
  custodyDurationDays: number;
  offence: string;
  court: string;
  status: CaseStatus;
  urgency: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
  documents: DocumentInfo[];
  readinessScore: number;
  eligibilityScore: number;
  evidenceChain: EvidenceNode[];
  legalSources: LegalSource[];
  timeline: { date: string; title: string; status: "completed" | "current" | "stalled" | "pending"; description?: string }[];
  flagReasoning: string[];
}

export const MOCK_CASES: Case[] = [
  {
    id: "TN-2026-00482",
    prisonerName: "Ravi Kumar",
    age: 34,
    custodyDurationDays: 913,
    offence: "Theft (Sec 379 IPC)",
    court: "District Sessions Court, Chennai",
    status: "LEGAL_REVIEW",
    urgency: "URGENT",
    readinessScore: 82,
    eligibilityScore: 100,
    flagReasoning: [
      "Custody duration extracted: 913 days",
      "Maximum sentence identified: 3 years (1095 days)",
      "Applicable statutory threshold calculated: 1/2 of max sentence (547 days)",
      "Relevant legal provision retrieved: BNSS Section 479"
    ],
    documents: [
      { id: "d1", name: "Remand Order", type: "Remand Order", status: "available" },
      { id: "d2", name: "Charge Sheet", type: "Charge Sheet", status: "available" },
      { id: "d3", name: "Custody Record", type: "Custody Record", status: "available" },
      { id: "d4", name: "Previous Bail Order", type: "Previous Bail Order", status: "missing" },
      { id: "d5", name: "Latest Hearing Order", type: "Latest Hearing Order", status: "missing" },
      { id: "d6", name: "Identity Record", type: "Identity Record", status: "available" },
    ],
    evidenceChain: [
      { id: "e1", type: "FACT", title: "Custody Duration", description: "913 Days in continuous custody" },
      { id: "e2", type: "DOCUMENT", title: "Custody Record", description: "Central Prison Database Extract", sourceDocId: "d3" },
      { id: "e3", type: "EXTRACTION", title: "Date of Remand", description: "14-03-2024", confidence: 97, sourceDocId: "d1" },
      { id: "e4", type: "CALCULATION", title: "Threshold Exceeded", description: "913 > 547 (50% of 3 years)" },
      { id: "e5", type: "LEGAL_SOURCE", title: "BNSS Sec 479", description: "Under-trial prisoner serving > 1/2 max sentence is eligible for bail." },
      { id: "e6", type: "CONCLUSION", title: "Statutory Bail Eligible", description: "Requires immediate application under Sec 479." }
    ],
    legalSources: [
      {
        id: "ls1",
        section: "BNSS Section 479",
        relevance: 98,
        passage: "Where a person has, during the period of investigation, inquiry or trial under this Sanhita of an offence under any law... undergone detention for a period extending up to one-half of the maximum period of imprisonment specified for that offence by that law, he shall be released by the Court on bail.",
        reasoning: "The prisoner has served 913 days, which exceeds the 547-day threshold (half of the 3-year maximum sentence for Sec 379 IPC)."
      }
    ],
    timeline: [
      { date: "12 MAR 2024", title: "Arrest", status: "completed" },
      { date: "14 MAR 2024", title: "Remand", status: "completed" },
      { date: "08 APR 2024", title: "Charge Sheet Filed", status: "completed" },
      { date: "21 JUN 2024", title: "First Hearing", status: "completed" },
      { date: "08 AUG 2026", title: "Eligibility threshold detected", status: "current" },
      { date: "Pending", title: "Latest hearing order not received", status: "stalled", description: "CASE STALLED HERE" },
    ]
  },
  {
    id: "KA-2026-00129",
    prisonerName: "Syed Ahmed",
    age: 42,
    custodyDurationDays: 450,
    offence: "Cheating (Sec 420 IPC)",
    court: "Magistrate Court, Bengaluru",
    status: "DOCUMENTS_PENDING",
    urgency: "MEDIUM",
    readinessScore: 65,
    eligibilityScore: 40,
    flagReasoning: [
      "Custody duration extracted: 450 days",
      "Approaching 1/2 max sentence threshold in 15 days",
    ],
    documents: [
      { id: "d1", name: "Remand Order", type: "Remand Order", status: "available" },
      { id: "d2", name: "Charge Sheet", type: "Charge Sheet", status: "missing" },
      { id: "d3", name: "Custody Record", type: "Custody Record", status: "available" },
    ],
    evidenceChain: [],
    legalSources: [],
    timeline: [
      { date: "10 MAY 2025", title: "Arrest", status: "completed" },
      { date: "11 MAY 2025", title: "Remand", status: "completed" },
      { date: "Pending", title: "Charge Sheet Pending", status: "stalled", description: "CASE STALLED HERE" },
    ]
  },
  {
    id: "MH-2026-00993",
    prisonerName: "Priya Desai",
    age: 28,
    custodyDurationDays: 120,
    offence: "Forgery (Sec 465 IPC)",
    court: "Sessions Court, Mumbai",
    status: "VERIFIED",
    urgency: "LOW",
    readinessScore: 90,
    eligibilityScore: 10,
    flagReasoning: [
      "All documents verified.",
      "Not currently eligible for statutory bail."
    ],
    documents: [
      { id: "d1", name: "Remand Order", type: "Remand Order", status: "available" },
      { id: "d2", name: "Charge Sheet", type: "Charge Sheet", status: "available" },
      { id: "d3", name: "Custody Record", type: "Custody Record", status: "available" },
    ],
    evidenceChain: [],
    legalSources: [],
    timeline: [
      { date: "01 APR 2026", title: "Arrest", status: "completed" },
      { date: "02 APR 2026", title: "Remand", status: "completed" },
      { date: "15 MAY 2026", title: "Charge Sheet Filed", status: "completed" },
    ]
  }
];

export const DASHBOARD_METRICS = {
  monitored: 1284,
  potentiallyEligible: 127,
  missingDocuments: 34,
  awaitingReview: 18,
  urgentActions: 7
};
