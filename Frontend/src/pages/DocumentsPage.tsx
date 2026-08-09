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
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-sm text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Document Vault
            </span>
            <span className="text-xs text-muted-foreground font-mono">Completeness Agent Sync</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Legal Records & File Vault</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Central repository for Remand Orders, Charge Sheets, and DLSA certificates required for bail motions.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="px-4 py-2 bg-accent text-accent-foreground font-semibold rounded text-sm hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-accent/20"
        >
          <Plus className="w-4 h-4" /> Upload Document
        </button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="p-6 rounded bg-card shadow-sm border border-border flex items-center gap-4">
          <div className="w-12 h-12 rounded bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-primary">{docs.length}</div>
            <div className="text-xs text-muted-foreground">Total Documents Tracked</div>
          </div>
        </div>

        <div className="p-6 rounded bg-card shadow-sm border border-border flex items-center gap-4">
          <div className="w-12 h-12 rounded bg-muted border border-border flex items-center justify-center text-foreground">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-primary">{presentCount}</div>
            <div className="text-xs text-muted-foreground">Verified & On Record</div>
          </div>
        </div>

        <div className="p-6 rounded bg-card shadow-sm border border-border flex items-center gap-4">
          <div className="w-12 h-12 rounded bg-destructive/10 border border-destructive/20 flex items-center justify-center text-destructive">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-primary">{missingCount}</div>
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
          className="w-full pl-10 pr-4 py-2 bg-card/70 border border-border rounded text-sm text-primary focus:outline-none focus:border-accent"
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Loading document inventory from FastAPI service...
        </div>
      ) : (
        <div className="bg-card shadow-sm border border-border rounded overflow-hidden backdrop-blur-md">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-muted-foreground">
              <thead className="bg-card/70 text-xs font-semibold text-primary uppercase border-b border-border">
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
                  <tr key={d.id} className="hover:bg-card shadow-sm transition-colors">
                    <td className="px-6 py-4 font-mono text-accent font-semibold">{d.case_id}</td>
                    <td className="px-6 py-4 text-primary font-medium">{d.document_type}</td>
                    <td className="px-6 py-4 text-muted-foreground">{d.prisoner_name}</td>
                    <td className="px-6 py-4">
                      {d.is_present ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm text-xs font-medium bg-muted text-foreground border border-border">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Present
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm text-xs font-medium bg-destructive/10 text-destructive border border-destructive/20">
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
                          className="px-3 py-1 bg-secondary/50 hover:bg-secondary text-primary rounded-sm text-xs font-medium border border-border transition-colors inline-flex items-center gap-1"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-primary backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-background border border-border rounded p-6 space-y-6 shadow-2xl">
            <h3 className="text-lg font-bold text-primary">Upload Missing Document</h3>
            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Target Case ID</label>
                <input
                  type="text"
                  value={uploadCaseId}
                  onChange={e => setUploadCaseId(e.target.value)}
                  className="w-full px-3 py-2 bg-secondary/50 border border-border rounded text-primary text-sm"
                  required
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1">Document Type</label>
                <select
                  value={uploadDocType}
                  onChange={e => setUploadDocType(e.target.value)}
                  className="w-full px-3 py-2 bg-secondary/50 border border-border rounded text-primary text-sm"
                >
                  <option value="charge_sheet" className="bg-background">Charge Sheet</option>
                  <option value="remand_order" className="bg-background">Remand Order</option>
                  <option value="prior_bail_order_if_any" className="bg-background">Prior Bail Order</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 bg-secondary/50 text-primary rounded text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-4 py-2 bg-accent text-accent-foreground rounded text-xs font-semibold hover:opacity-90 transition-opacity"
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
