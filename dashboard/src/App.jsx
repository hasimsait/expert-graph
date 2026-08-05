import React, { useState, useEffect, useCallback } from 'react';
import StatsHeader from './components/StatsHeader';
import { 
  Check, 
  X, 
  ChevronRight, 
  Keyboard, 
  Send, 
  Layers, 
  FileText, 
  Share2, 
  AlertCircle,
  ExternalLink
} from 'lucide-react';

export default function App() {
  const [queue, setQueue] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(true);
  const [ingestText, setIngestText] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const fetchQueueAndStats = useCallback(async () => {
    setLoading(true);
    try {
      const [queueRes, statsRes] = await Promise.all([
        fetch('/api/queue?limit=50'),
        fetch('/api/stats')
      ]);
      const queueData = await queueRes.json();
      const statsData = await statsRes.json();

      setQueue(queueData.queue || []);
      setStats(statsData);
      setCurrentIndex(0);
    } catch (err) {
      console.error("Failed to load queue or stats:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueueAndStats();
  }, [fetchQueueAndStats]);

  const currentItem = queue[currentIndex];

  const handleApprove = async () => {
    if (!currentItem) return;
    try {
      await fetch(`/api/approve/${currentItem.edge_id}`, { method: 'POST' });
      setStats(prev => ({ ...prev, pending: Math.max(0, prev.pending - 1), approved: prev.approved + 1 }));
      showFeedback('Approved', 'success');
      nextItem();
    } catch (err) {
      console.error("Approve failed:", err);
    }
  };

  const handleReject = async () => {
    if (!currentItem) return;
    try {
      await fetch(`/api/reject/${currentItem.edge_id}`, { method: 'POST' });
      setStats(prev => ({ ...prev, pending: Math.max(0, prev.pending - 1), rejected: prev.rejected + 1 }));
      showFeedback('Rejected', 'danger');
      nextItem();
    } catch (err) {
      console.error("Reject failed:", err);
    }
  };

  const nextItem = () => {
    if (currentIndex < queue.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else {
      fetchQueueAndStats();
    }
  };

  const showFeedback = (msg, type) => {
    setFeedback({ msg, type });
    setTimeout(() => setFeedback(null), 1200);
  };

  // Global Keyboard Shortcuts (A, R, N, ArrowRight, Enter, Backspace)
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in textarea
      if (document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT') {
        return;
      }
      if (e.key === 'a' || e.key === 'A' || e.key === 'Enter') {
        e.preventDefault();
        handleApprove();
      } else if (e.key === 'r' || e.key === 'R' || e.key === 'Backspace' || e.key === 'Delete') {
        e.preventDefault();
        handleReject();
      } else if (e.key === 'n' || e.key === 'N' || e.key === 'ArrowRight') {
        e.preventDefault();
        nextItem();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentItem, currentIndex, queue]);

  const handleRunSieve = async (e) => {
    e.preventDefault();
    if (!ingestText.trim()) return;
    setIngesting(true);
    try {
      await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: ingestText })
      });
      setIngestText('');
      await fetchQueueAndStats();
      showFeedback('Sieve Ingestion Complete!', 'success');
    } catch (err) {
      console.error("Sieve ingestion failed:", err);
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans">
      
      {/* Top Header */}
      <StatsHeader stats={stats} onRefresh={fetchQueueAndStats} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Sieve Pipeline & Source Context (5 cols) */}
        <div className="lg:col-span-5 space-y-6 flex flex-col">
          
          {/* Quick Ingestion Sieve Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Send className="w-4 h-4 text-indigo-400" />
              Run Ingestion Sieve
            </h2>
            <form onSubmit={handleRunSieve} className="space-y-3">
              <textarea
                value={ingestText}
                onChange={(e) => setIngestText(e.target.value)}
                placeholder="Paste raw text chunk to extract pending facts (e.g., 'Acme Corp owes $5,000,000 to Global Bank')..."
                className="w-full h-24 bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
              />
              <button
                type="submit"
                disabled={ingesting || !ingestText.trim()}
                className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-indigo-600/20"
              >
                {ingesting ? 'Extractor & Critic Running...' : 'Extract & Push to Pending Queue'}
              </button>
            </form>
          </div>

          {/* Raw Text Chunk Display */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-3">
              <h2 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                Raw Source Text Context
              </h2>
              {currentItem && (
                <span className="text-[11px] font-mono text-slate-500">
                  ID: {currentItem.chunk_id}
                </span>
              )}
            </div>

            {currentItem ? (
              <div className="flex-1 bg-slate-950 border border-slate-800/80 rounded-xl p-4 text-sm text-slate-300 leading-relaxed overflow-y-auto font-sans">
                {currentItem.chunk_text}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-slate-500 text-xs text-center p-6 border border-dashed border-slate-800 rounded-xl">
                No items in pending queue. Run the Sieve above to populate candidate triples.
              </div>
            )}
          </div>

          {/* Keyboard Shortcuts Legend */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 text-xs space-y-2">
            <div className="flex items-center space-x-2 text-indigo-400 font-medium">
              <Keyboard className="w-4 h-4" />
              <span>High-Throughput Hotkeys</span>
            </div>
            <div className="grid grid-cols-3 gap-2 pt-1 font-mono text-[11px]">
              <div className="px-2.5 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-800/50 text-emerald-300 flex items-center justify-between">
                <span>Approve</span>
                <kbd className="bg-emerald-900/80 px-1.5 py-0.5 rounded text-[10px]">A</kbd>
              </div>
              <div className="px-2.5 py-1.5 rounded-lg bg-rose-950/60 border border-rose-800/50 text-rose-300 flex items-center justify-between">
                <span>Reject</span>
                <kbd className="bg-rose-900/80 px-1.5 py-0.5 rounded text-[10px]">R</kbd>
              </div>
              <div className="px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-between">
                <span>Skip</span>
                <kbd className="bg-slate-700 px-1.5 py-0.5 rounded text-[10px]">N</kbd>
              </div>
            </div>
          </div>

        </div>

        {/* Right Side: Candidate Graph Edge Verification Card (7 cols) */}
        <div className="lg:col-span-7 flex flex-col">
          
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex-1 flex flex-col justify-between relative overflow-hidden">
            
            {/* Feedback Floating Banner */}
            {feedback && (
              <div className={`absolute top-4 right-4 px-4 py-2 rounded-xl font-bold text-xs shadow-xl animate-bounce border ${
                feedback.type === 'success' ? 'bg-emerald-950 text-emerald-300 border-emerald-500' : 'bg-rose-950 text-rose-300 border-rose-500'
              }`}>
                {feedback.msg}
              </div>
            )}

            <div>
              {/* Card Header */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    Proposed Data-Graph Edge
                    <span className="text-xs font-mono font-normal text-slate-400">
                      ({currentIndex + 1} of {queue.length})
                    </span>
                  </h2>
                  <p className="text-xs text-slate-400">Cross-referenced against Meta-Graph ontology</p>
                </div>
                
                <a 
                  href="/ui/facts-widget" 
                  target="_blank" 
                  rel="noreferrer"
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 bg-indigo-950/50 border border-indigo-800/40 px-3 py-1.5 rounded-lg transition-colors"
                >
                  <span>Preview MCP-UI Widget</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              {loading ? (
                <div className="py-24 text-center text-slate-400 text-sm">
                  Loading candidate edges from Neo4j...
                </div>
              ) : currentItem ? (
                <div className="space-y-6">
                  
                  {/* Meta-Graph Ontology Lineage */}
                  {currentItem.meta_concept && (
                    <div className="p-3 rounded-xl bg-indigo-950/30 border border-indigo-800/40 flex items-center justify-between">
                      <div className="flex items-center space-x-2 text-xs">
                        <Layers className="w-4 h-4 text-indigo-400" />
                        <span className="text-slate-400">Ontology Mapping:</span>
                        <span className="font-mono text-indigo-300 font-semibold">{currentItem.relation}</span>
                        <span className="text-slate-500">[{currentItem.meta_mapping || 'SUBCLASS_OF'}]</span>
                        <span className="font-mono text-indigo-400 font-bold">{currentItem.meta_concept}</span>
                      </div>
                    </div>
                  )}

                  {/* Triplet Visual Display */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center bg-slate-950 p-6 rounded-2xl border border-slate-800">
                    
                    {/* Subject Node */}
                    <div className="p-4 rounded-xl bg-blue-950/50 border border-blue-800/60 text-center space-y-1">
                      <span className="text-[10px] uppercase font-bold text-blue-400 tracking-wider">
                        {currentItem.subject.type || 'ENTITY'}
                      </span>
                      <h3 className="text-base font-bold text-blue-200 font-mono">
                        {currentItem.subject.name}
                      </h3>
                    </div>

                    {/* Relation Edge */}
                    <div className="text-center space-y-2">
                      <div className="inline-block px-3 py-1 rounded-lg bg-indigo-950 border border-indigo-800/80 text-indigo-300 font-mono font-bold text-xs uppercase tracking-wider">
                        {currentItem.relation}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Confidence: {(currentItem.confidence * 100).toFixed(0)}%
                      </div>
                    </div>

                    {/* Object Node */}
                    <div className="p-4 rounded-xl bg-purple-950/50 border border-purple-800/60 text-center space-y-1">
                      <span className="text-[10px] uppercase font-bold text-purple-400 tracking-wider">
                        {currentItem.object.type || 'ENTITY'}
                      </span>
                      <h3 className="text-base font-bold text-purple-200 font-mono">
                        {currentItem.object.name}
                      </h3>
                    </div>

                  </div>

                </div>
              ) : (
                <div className="py-24 text-center text-slate-500 space-y-2">
                  <p className="text-base font-medium">All pending candidate facts have been evaluated!</p>
                  <p className="text-xs">No pending items remaining in queue.</p>
                </div>
              )}

            </div>

            {/* Action Buttons Footer */}
            {currentItem && (
              <div className="pt-6 border-t border-slate-800 grid grid-cols-3 gap-4 mt-8">
                
                <button
                  onClick={handleReject}
                  className="py-4 px-4 bg-rose-950/80 hover:bg-rose-900 border border-rose-800/80 text-rose-200 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-rose-900/30 group"
                >
                  <X className="w-5 h-5 text-rose-400 group-hover:scale-110 transition-transform" />
                  <span>Reject (R)</span>
                </button>

                <button
                  onClick={nextItem}
                  className="py-4 px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all"
                >
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                  <span>Skip (N)</span>
                </button>

                <button
                  onClick={handleApprove}
                  className="py-4 px-4 bg-emerald-600 hover:bg-emerald-500 border border-emerald-500 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-600/20 group"
                >
                  <Check className="w-5 h-5 text-white group-hover:scale-110 transition-transform" />
                  <span>Approve Fact (A)</span>
                </button>

              </div>
            )}

          </div>

        </div>

      </main>
    </div>
  );
}
