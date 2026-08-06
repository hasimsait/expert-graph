import React, { useState, useEffect, useCallback } from 'react';
import StatsHeader from './components/StatsHeader';
import FactCard from './components/FactCard';
import AnalyticsModal from './components/AnalyticsModal';
import { 
  Keyboard, 
  Send, 
  FileText
} from 'lucide-react';

export default function App() {
  const [queue, setQueue] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(true);
  const [ingestText, setIngestText] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState(false);

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
      <StatsHeader
        stats={stats}
        onRefresh={fetchQueueAndStats}
        onOpenAnalytics={() => setIsAnalyticsOpen(true)}
      />

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
          <FactCard
            currentItem={currentItem}
            currentIndex={currentIndex}
            totalItems={queue.length}
            loading={loading}
            onApprove={handleApprove}
            onReject={handleReject}
            onNext={nextItem}
            feedback={feedback}
          />
        </div>

      </main>

      {/* Knowledge Graph Analytics & Implications Modal */}
      <AnalyticsModal
        isOpen={isAnalyticsOpen}
        onClose={() => setIsAnalyticsOpen(false)}
        initialDocumentId={currentItem?.chunk_id || 'doc_101'}
      />
    </div>
  );
}
