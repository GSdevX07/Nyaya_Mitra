import { useParams, Link } from "react-router-dom";
import { MOCK_CASES } from "@/data/mock";
import { ArrowLeft, FileText, CheckCircle2, AlertTriangle, AlertCircle, Scale, Calculator, Link as LinkIcon, Download, Search, PenTool, Check, X, Activity } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

export function CaseIntelligence() {
  const { id } = useParams();
  const caseData = MOCK_CASES.find(c => c.id === id) || MOCK_CASES[0];
  const [selectedEvidence, setSelectedEvidence] = useState(caseData.evidenceChain[1] || null);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-12">
      
      {/* Header */}
      <div className="space-y-6">
        <Link to="/dashboard" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Command Center
        </Link>

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <h1 className="text-4xl font-semibold tracking-tight text-white">CASE #{caseData.id}</h1>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold border uppercase tracking-wider ${
                caseData.urgency === 'URGENT' ? 'bg-destructive/10 text-destructive border-destructive/20' : 
                'bg-accent/10 text-accent border-accent/20'
              }`}>
                {caseData.urgency}
              </span>
            </div>
            
            <div className="flex flex-wrap gap-6 text-sm">
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Prisoner</span>
                <p className="text-white font-medium text-lg">{caseData.prisonerName} <span className="text-muted-foreground text-sm font-normal">({caseData.age}y)</span></p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Custody Duration</span>
                <p className="text-white font-medium text-lg">{caseData.custodyDurationDays} days</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Offence</span>
                <p className="text-white font-medium text-lg">{caseData.offence}</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Court</span>
                <p className="text-white font-medium text-lg">{caseData.court}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-accent/10 border border-accent/20 px-6 py-4 rounded-xl text-right">
            <div className="text-xs text-accent uppercase tracking-wider font-semibold mb-1">Status</div>
            <div className="text-lg text-white font-medium">POTENTIALLY ELIGIBLE — HUMAN VERIFICATION REQUIRED</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Why Was This Case Flagged */}
          <section className="p-8 rounded-xl border border-white/5 bg-white/[0.02] space-y-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-5">
              <AlertCircle className="w-48 h-48" />
            </div>
            <div className="relative z-10">
              <h2 className="text-xl font-medium tracking-tight text-white mb-6 uppercase">Why this case requires attention</h2>
              
              <div className="space-y-4">
                {caseData.flagReasoning.map((reason, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                    <span className="text-white/90 leading-relaxed">{reason}</span>
                  </div>
                ))}
              </div>

              <div className="mt-8 pt-6 border-t border-white/5 space-y-3">
                {caseData.documents.filter(d => d.status === "missing").map(doc => (
                  <div key={doc.id} className="flex items-start gap-3 text-amber-500">
                    <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                    <span className="leading-relaxed">Missing {doc.name.toLowerCase()} documentation</span>
                  </div>
                ))}
              </div>

              <div className="mt-8 flex gap-4 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                <div className="flex items-center gap-1"><FileText className="w-4 h-4 text-emerald-500" /> FACT</div>
                <div className="flex items-center gap-1"><Calculator className="w-4 h-4 text-blue-500" /> CALCULATION</div>
                <div className="flex items-center gap-1"><Scale className="w-4 h-4 text-amber-500" /> LEGAL SOURCE</div>
                <div className="flex items-center gap-1"><Activity className="w-4 h-4 text-accent" /> AI INTERPRETATION</div>
              </div>
            </div>
          </section>

          {/* Evidence Chain */}
          <section className="space-y-4">
            <h2 className="text-xl font-medium tracking-tight uppercase text-white flex items-center gap-2">
              <LinkIcon className="w-5 h-5 text-accent" /> Evidence Chain
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Chain Diagram */}
              <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02] space-y-4 relative">
                <div className="absolute left-8 top-10 bottom-10 w-px bg-white/10" />
                {caseData.evidenceChain.map((node, idx) => (
                  <div 
                    key={node.id} 
                    className={`relative z-10 pl-10 cursor-pointer transition-opacity ${selectedEvidence?.id === node.id ? 'opacity-100' : 'opacity-50 hover:opacity-100'}`}
                    onClick={() => setSelectedEvidence(node)}
                  >
                    <div className={`absolute left-0 top-1.5 w-4 h-4 rounded-full border-2 ${
                      node.type === 'FACT' ? 'border-emerald-500 bg-background' :
                      node.type === 'CALCULATION' ? 'border-blue-500 bg-background' :
                      node.type === 'LEGAL_SOURCE' ? 'border-amber-500 bg-background' :
                      'border-accent bg-accent'
                    }`} />
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">{node.type}</div>
                    <div className="text-white font-medium">{node.title}</div>
                    <div className="text-sm text-muted-foreground mt-1">{node.description}</div>
                  </div>
                ))}
              </div>

              {/* Document Split Screen Mock */}
              <div className="rounded-xl border border-white/5 bg-black/50 overflow-hidden flex flex-col">
                <div className="bg-white/5 p-3 text-xs font-medium text-muted-foreground uppercase tracking-wider flex justify-between items-center">
                  <span>Source Verification</span>
                  {selectedEvidence?.confidence && <span className="text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded">Extracted with {selectedEvidence.confidence}% confidence</span>}
                </div>
                <div className="p-6 flex-1 relative flex items-center justify-center text-center">
                  <div className="absolute inset-0 opacity-20 bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
                  {selectedEvidence?.sourceDocId ? (
                    <div className="space-y-4 relative z-10">
                      <FileText className="w-12 h-12 text-white/20 mx-auto" />
                      <div className="text-white/50 text-sm">Document preview unavailable in demo</div>
                      <div className="p-4 bg-accent/10 border border-accent/20 rounded text-accent text-sm text-left">
                        <div className="font-medium mb-2">Extracted Text:</div>
                        "...remanded to judicial custody until <span className="bg-accent/30 text-white font-bold px-1 rounded">14-03-2024</span>..."
                      </div>
                    </div>
                  ) : (
                    <div className="text-white/30 text-sm">Select a document node to view source</div>
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* Legal Evidence / RAG */}
          <section className="space-y-4">
             <h2 className="text-xl font-medium tracking-tight uppercase text-white flex items-center gap-2">
              <Scale className="w-5 h-5 text-accent" /> Legal Evidence
            </h2>
            {caseData.legalSources.map(source => (
              <div key={source.id} className="p-6 rounded-xl border border-white/5 bg-white/[0.02] space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="text-lg font-medium text-white mb-1">{source.section}</div>
                    <div className="text-xs text-muted-foreground uppercase tracking-wider">Source Code of Criminal Procedure</div>
                  </div>
                  <div className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 px-3 py-1 rounded-full text-xs font-semibold">
                    {source.relevance}% RELEVANCE
                  </div>
                </div>
                <div className="p-4 bg-black/40 rounded-lg border border-white/5 text-sm text-white/80 font-serif leading-relaxed italic">
                  "{source.passage}"
                </div>
                <div>
                  <div className="text-xs font-medium text-accent uppercase tracking-wider mb-2">Why this source matters</div>
                  <p className="text-sm text-white/90">{source.reasoning}</p>
                </div>
              </div>
            ))}
          </section>

        </div>

        {/* Right Column */}
        <div className="space-y-8">
          
          {/* Document Readiness */}
          <section className="p-6 rounded-xl border border-white/5 bg-white/[0.02] space-y-6">
            <h2 className="text-lg font-medium tracking-tight uppercase text-white">Document Readiness</h2>
            <div className="space-y-3">
              {caseData.documents.map(doc => (
                <div key={doc.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {doc.status === "available" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <X className="w-4 h-4 text-destructive" />
                    )}
                    <span className={`text-sm ${doc.status === "available" ? "text-white" : "text-muted-foreground"}`}>{doc.name}</span>
                  </div>
                  {doc.status === "missing" && (
                    <button className="text-xs text-accent hover:text-accent/80 font-medium">Request</button>
                  )}
                </div>
              ))}
            </div>
            
            {caseData.documents.some(d => d.status === "missing") && (
              <div className="mt-6 p-4 bg-accent/5 border border-accent/10 rounded-lg">
                <div className="text-xs font-medium text-accent uppercase tracking-wider mb-2">Action Required</div>
                <p className="text-xs text-muted-foreground mb-3">Generate automated records request to central registry.</p>
                <button className="w-full py-2 bg-white/5 hover:bg-white/10 text-white text-xs font-medium rounded transition-colors flex items-center justify-center gap-2">
                  <Download className="w-3 h-3" /> Generate Request PDF
                </button>
              </div>
            )}
          </section>

          {/* Case Timeline */}
          <section className="p-6 rounded-xl border border-white/5 bg-white/[0.02] space-y-6">
            <h2 className="text-lg font-medium tracking-tight uppercase text-white">Case Timeline</h2>
            <div className="space-y-6 relative">
              <div className="absolute left-2 top-2 bottom-2 w-px bg-white/10" />
              {caseData.timeline.map((event, idx) => (
                <div key={idx} className="relative z-10 pl-8">
                  <div className={`absolute left-1 top-1 w-2.5 h-2.5 rounded-full ${
                    event.status === "completed" ? "bg-emerald-500" :
                    event.status === "current" ? "bg-accent animate-pulse" :
                    event.status === "stalled" ? "bg-destructive" :
                    "bg-white/20"
                  }`} />
                  <div className="text-xs text-muted-foreground mb-1">{event.date}</div>
                  <div className={`text-sm font-medium ${event.status === "stalled" ? "text-destructive" : "text-white"}`}>{event.title}</div>
                  {event.description && (
                    <div className="mt-1 text-xs font-semibold text-destructive uppercase tracking-wider bg-destructive/10 inline-block px-2 py-0.5 rounded border border-destructive/20">
                      {event.description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Human Review Gateway */}
          <section className="p-6 rounded-xl border border-accent/30 bg-accent/5 space-y-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-accent/10 blur-3xl rounded-full" />
            <h2 className="text-lg font-semibold tracking-tight uppercase text-white relative z-10">Human Review Required</h2>
            
            <div className="space-y-3 relative z-10">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">AI analysis complete</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Evidence collected</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Draft prepared</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 space-y-4 relative z-10">
              <div className="text-center">
                <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Legal Review</div>
                <div className="text-xl font-bold text-accent">PENDING</div>
              </div>
              
              <div className="p-3 bg-black/40 border border-white/5 rounded text-xs text-muted-foreground leading-relaxed text-center">
                "I confirm that I have reviewed the supporting documents and legal basis."
              </div>

              <div className="space-y-2">
                <button className="w-full py-3 bg-white text-black font-semibold rounded hover:bg-white/90 transition-colors flex justify-center items-center gap-2">
                  <Check className="w-4 h-4" /> Approve for Filing
                </button>
                <div className="grid grid-cols-2 gap-2">
                  <button className="py-2 bg-white/5 hover:bg-white/10 text-white font-medium rounded transition-colors text-xs flex justify-center items-center gap-2">
                    <PenTool className="w-3 h-3" /> Request Changes
                  </button>
                  <button className="py-2 bg-destructive/10 hover:bg-destructive/20 text-destructive font-medium rounded transition-colors text-xs flex justify-center items-center gap-2">
                    <X className="w-3 h-3" /> Reject
                  </button>
                </div>
              </div>
              <div className="text-center text-[10px] text-muted-foreground uppercase tracking-widest mt-4">
                AI NEVER FILES AUTONOMOUSLY
              </div>
            </div>
          </section>

        </div>

      </div>
    </div>
  );
}
