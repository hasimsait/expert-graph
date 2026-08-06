import React, { useState, useEffect } from 'react';
import { X, Network, ArrowRight, Award, Search, RefreshCw, FileText, Database } from 'lucide-react';

export default function AnalyticsModal({ isOpen, onClose, initialDocumentId = '' }) {
  const [activeTab, setActiveTab] = useState('implications');
  const [docId, setDocId] = useState(initialDocumentId || 'ALL');
  const [documents, setDocuments] = useState([]);
  const [implications, setImplications] = useState([]);
  const [pagerankConcepts, setPagerankConcepts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch available real documents dynamically from backend on modal open
  useEffect(() => {
    if (isOpen) {
      fetchAvailableDocuments();
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      if (activeTab === 'implications') {
        fetchImplications(docId || 'ALL');
      } else {
        fetchPageRank();
      }
    }
  }, [isOpen, activeTab, docId]);

  const fetchAvailableDocuments = async () => {
    try {
      const [docsRes, queueRes] = await Promise.all([
        fetch('/api/analytics/documents'),
        fetch('/api/queue')
      ]);
      const docsData = await docsRes.json();
      const queueData = await queueRes.json();

      const docList = docsData.documents || [];
      const queueItems = queueData.queue || [];

      // Combine and deduplicate real document IDs from Neo4j & pending queue
      const combined = [...docList];
      const seen = new Set(docList.map(d => d.id));

      for (const item of queueItems) {
        if (item.chunk_id && !seen.has(item.chunk_id)) {
          seen.add(item.chunk_id);
          const chunkText = item.chunk_text || "";
          const title = chunkText ? (chunkText.slice(0, 30) + "...") : item.chunk_id;
          combined.push({ id: item.chunk_id, title, type: "Pending Chunk" });
        }
      }

      setDocuments(combined);
      if (initialDocumentId) {
        setDocId(initialDocumentId);
      } else if (combined.length > 0) {
        setDocId(combined[0].id);
      }
    } catch (err) {
      console.error("Failed to load real documents:", err);
    }
  };

  const fetchImplications = async (idToFetch) => {
    const targetId = idToFetch || 'ALL';
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/analytics/implications/${encodeURIComponent(targetId)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setImplications(data.implications || []);
    } catch (err) {
      console.error("Failed to fetch implications:", err);
      setError("Could not load 4-hop implications. Verify document selection or graph connectivity.");
      setImplications([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchPageRank = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/analytics/pagerank/concepts');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPagerankConcepts(data.top_concepts || []);
    } catch (err) {
      console.error("Failed to fetch PageRank concepts:", err);
      setError("Could not run PageRank / Centrality analysis.");
      setPagerankConcepts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDoc = (selectedId) => {
    setDocId(selectedId);
    fetchImplications(selectedId);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-indigo-950 border border-indigo-800/80 text-indigo-400">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Knowledge Graph Analytics & Implications
              </h2>
              <p className="text-xs text-slate-400">
                Neo4j Graph Data Science & 4-Hop Multi-Domain Traversals
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 pt-4 border-b border-slate-800 bg-slate-950/50 flex space-x-4">
          <button
            onClick={() => setActiveTab('implications')}
            className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'implications'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>4-Hop Document Implications (/api/analytics/implications)</span>
          </button>

          <button
            onClick={() => setActiveTab('pagerank')}
            className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'pagerank'
                ? 'border-purple-500 text-purple-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Award className="w-4 h-4" />
            <span>Concept Hub Centrality & PageRank (/api/analytics/pagerank)</span>
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 flex-1 overflow-y-auto space-y-4">
          
          {error && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          {activeTab === 'implications' ? (
            <div className="space-y-4">
              
              {/* Real Documents Selector */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold uppercase tracking-wider text-[10px] flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-indigo-400" />
                    Active Graph Documents ({documents.length}):
                  </span>
                  <span className="text-slate-500 font-mono text-[11px]">Click a document to traverse</span>
                </div>
                
                <div className="flex flex-wrap gap-2 max-h-28 overflow-y-auto pr-1">
                  <button
                    onClick={() => handleSelectDoc('ALL')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold border transition-all ${
                      docId === 'ALL'
                        ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/30'
                        : 'bg-slate-950 text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white'
                    }`}
                  >
                    🌐 ALL DOCUMENTS
                  </button>

                  {documents.map((doc) => (
                    <button
                      key={doc.id}
                      onClick={() => handleSelectDoc(doc.id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-mono font-medium border transition-all ${
                        docId === doc.id
                          ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/30'
                          : 'bg-slate-950 text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white'
                      }`}
                      title={doc.title}
                    >
                      📄 {doc.id} ({doc.title ? doc.title.slice(0, 20) + "..." : "Doc"})
                    </button>
                  ))}
                </div>
              </div>

              {/* Document ID Input / Search Bar */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  fetchImplications(docId);
                }}
                className="flex items-center gap-3 bg-slate-950 p-2.5 rounded-xl border border-slate-800"
              >
                <Search className="w-4 h-4 text-slate-500 ml-1" />
                <input
                  type="text"
                  value={docId}
                  onChange={(e) => setDocId(e.target.value)}
                  placeholder="Selected Document ID..."
                  className="flex-1 bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none font-mono"
                />
                <button
                  type="submit"
                  disabled={loading || !docId.trim()}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Traverse'}
                </button>
              </form>

              {/* Implications Traversal Results */}
              {loading ? (
                <div className="py-16 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                  <span>Traversing 4-hop schema: SourceDocument → RawEntity → CanonicalConcept → DownstreamImplication...</span>
                </div>
              ) : implications.length > 0 ? (
                <div className="space-y-3">
                  <div className="text-xs text-slate-400 font-mono flex items-center justify-between">
                    <span>Discovered {implications.length} Downstream Implication Chain(s)</span>
                    <span className="text-indigo-400 font-semibold">Filter: {docId}</span>
                  </div>

                  {implications.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 hover:border-indigo-500/40 transition-colors"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                        <span className="text-xs font-mono font-bold text-indigo-300">
                          Document ID: {item.document_id}
                        </span>
                        <span className="text-[10px] uppercase font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60 font-mono">
                          Implication: {item.implication_id}
                        </span>
                      </div>

                      {/* 4-Hop Visual Chain */}
                      <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
                        <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-slate-300">
                          📄 {item.document_id}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-500" />

                        <span className="px-2.5 py-1 rounded-lg bg-blue-950/80 border border-blue-800/60 text-blue-300">
                          🏷️ {item.raw_entity}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-500" />

                        <span className="px-2.5 py-1 rounded-lg bg-purple-950/80 border border-purple-600/70 text-purple-200 font-bold">
                          🧠 {item.canonical_name} [{item.canonical_id}]
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-500" />

                        <span className="px-2.5 py-1 rounded-lg bg-emerald-950/80 border border-emerald-600/70 text-emerald-200 font-bold">
                          ⚡ {item.implication_name}
                        </span>
                      </div>

                      {item.description && (
                        <p className="text-xs text-slate-400 italic pt-1 border-t border-slate-900">
                          "{item.description}"
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-16 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-xl p-6 space-y-2">
                  <p className="font-medium text-slate-400">No downstream implications found for document <code className="text-indigo-400">{docId}</code>.</p>
                  <p className="text-[11px]">Click 'ALL DOCUMENTS' or run the Sieve to extract candidate graph paths.</p>
                </div>
              )}
            </div>
          ) : (
            /* PageRank Tab */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-mono">
                  Neo4j GDS PageRank & Centrality (CanonicalConcept Nodes)
                </span>
                <button
                  onClick={fetchPageRank}
                  disabled={loading}
                  className="px-3 py-1 rounded-lg bg-purple-950 hover:bg-purple-900 border border-purple-800/80 text-purple-300 text-xs font-mono flex items-center gap-1.5 transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  <span>Re-run PageRank</span>
                </button>
              </div>

              {loading ? (
                <div className="py-16 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />
                  <span>Running PageRank centrality algorithm on ontology concepts...</span>
                </div>
              ) : pagerankConcepts.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {pagerankConcepts.map((c, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between hover:border-purple-500/40 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold font-mono ${
                          idx === 0
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : 'bg-slate-900 text-slate-400 border border-slate-800'
                        }`}>
                          #{idx + 1}
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-white font-mono">
                            {c.concept_name}
                          </h4>
                          <span className="text-[10px] text-slate-500 font-mono">
                            ID: {c.concept_id}
                          </span>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="text-xs font-mono font-bold text-purple-300 block">
                          Score: {typeof c.score === 'number' ? c.score.toFixed(4) : c.score}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          Central Hub
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-16 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-xl p-6">
                  No concept PageRank scores available. Seed data or verify Neo4j concept nodes.
                </div>
              )}
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950 flex items-center justify-between text-[11px] text-slate-500">
          <span>ExpertGraph Multi-Hop Analytics Engine</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition-colors"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
