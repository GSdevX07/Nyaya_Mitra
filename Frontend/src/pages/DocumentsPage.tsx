import { useState, useEffect } from "react";
import { FileText, Upload, CheckCircle2, AlertTriangle, Search, Plus, ShieldCheck } from "lucide-react";
import { fetchDocuments, uploadDocument } from "@/lib/api";

interface DocItem {
  id: string;
  case_id: string;
  prisoner_name: string;
  document_type: string;
  status: string;
  is_present: boolean;
  uploaded_date?: string;
  jail_location: string;
}

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [uploadCaseId, setUploadCaseId] = useState("UTP-0015");
  const [uploadDocType, setUploadDocType] = useState("charge_sheet");
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const loadDocs = async () => {
    setLoading(true);
    const data = await fetchDocuments();
    setDocs(data);
    setLoading(false);
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploading(true);
    try {
      await uploadDocument(uploadCaseId, uploadDocType);
      await loadDocs();
      setShowUploadModal(false);
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  const filtered = docs.filter(d => 
    d.case_id.toLowerCase().includes(search.toLowerCase()) ||
    d.document_type.toLowerCase().includes(search.toLowerCase()) ||
    d.prisoner_name.toLowerCase().includes(search.toLowerCase())
  );

  const presentCount = docs.filter(d => d.is_present).length;
  const missingCount = docs.filter(d => !d.is_present).length;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Document Vault
            </span>
            <span className="text-xs text-muted-foreground font-mono">Completeness Agent Sync</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Legal Records & File Vault</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Central repository for Remand Orders, Charge Sheets, and DLSA certificates required for bail motions.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="px-4 py-2 bg-accent text-accent-foreground font-semibold rounded-xl text-sm hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-accent/20"
        >
          <Plus className="w-4 h-4" /> Upload Document
        </button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{docs.length}</div>
            <div className="text-xs text-muted-foreground">Total Documents Tracked</div>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{presentCount}</div>
            <div className="text-xs text-muted-foreground">Verified & On Record</div>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-destructive/10 border border-destructive/20 flex items-center justify-center text-destructive">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{missingCount}</div>
            <div className="text-xs text-muted-foreground">Missing Document Gaps</div>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" />
        <input
          type="text"
          placeholder="Search document vault by case ID or doc name..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-white/[0.03] border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-accent"
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Loading document inventory from FastAPI service...
        </div>
      ) : (
        <div className="bg-white/[0.02] border border-white/10 rounded-2xl overflow-hidden backdrop-blur-md">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-muted-foreground">
              <thead className="bg-white/[0.03] text-xs font-semibold text-white uppercase border-b border-white/10">
                <tr>
                  <th className="px-6 py-4">Case ID</th>
                  <th className="px-6 py-4">Document Type</th>
                  <th className="px-6 py-4">Prisoner Record</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Facility</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filtered.map(d => (
                  <tr key={d.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 font-mono text-accent font-semibold">{d.case_id}</td>
                    <td className="px-6 py-4 text-white font-medium">{d.document_type}</td>
                    <td className="px-6 py-4 text-white/80">{d.prisoner_name}</td>
                    <td className="px-6 py-4">
                      {d.is_present ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Present
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-destructive/10 text-destructive border border-destructive/20">
                          <AlertTriangle className="w-3.5 h-3.5" /> Missing Document
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">{d.jail_location}</td>
                    <td className="px-6 py-4 text-right">
                      {!d.is_present && (
                        <button
                          onClick={() => {
                            setUploadCaseId(d.case_id);
                            setUploadDocType(d.document_type.toLowerCase().replace(/ /g, "_"));
                            setShowUploadModal(true);
                          }}
                          className="px-3 py-1 bg-white/5 hover:bg-white/10 text-white rounded-lg text-xs font-medium border border-white/10 transition-colors inline-flex items-center gap-1"
                        >
                          <Upload className="w-3 h-3" /> Upload
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-background border border-white/10 rounded-2xl p-6 space-y-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Upload Missing Document</h3>
            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Target Case ID</label>
                <input
                  type="text"
                  value={uploadCaseId}
                  onChange={e => setUploadCaseId(e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-sm"
                  required
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1">Document Type</label>
                <select
                  value={uploadDocType}
                  onChange={e => setUploadDocType(e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-sm"
                >
                  <option value="charge_sheet" className="bg-background">Charge Sheet</option>
                  <option value="remand_order" className="bg-background">Remand Order</option>
                  <option value="prior_bail_order_if_any" className="bg-background">Prior Bail Order</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 bg-white/5 text-white rounded-xl text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-4 py-2 bg-accent text-accent-foreground rounded-xl text-xs font-semibold hover:opacity-90 transition-opacity"
                >
                  {uploading ? "Attaching..." : "Confirm & Attach"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
