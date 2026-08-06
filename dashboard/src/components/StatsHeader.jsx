import React from 'react';
import { CheckCircle2, XCircle, Clock, Sparkles, Network } from 'lucide-react';

export default function StatsHeader({ stats, onRefresh, onOpenAnalytics }) {
  return (
    <header className="bg-slate-900/90 border-b border-slate-800 backdrop-blur sticky top-0 z-40 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
            EG
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              ExpertGraph
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase tracking-wider font-semibold">
                Annotator Dashboard
              </span>
            </h1>
            <p className="text-xs text-slate-400">Thesis Ground-Truth Human-in-the-Loop Sieve</p>
          </div>
        </div>

        {/* Stats Counters & Analytics Action */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-amber-950/40 border border-amber-800/40 text-amber-300 text-xs">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span className="font-semibold">{stats.pending || 0}</span>
            <span className="text-amber-400/70">Pending</span>
          </div>

          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-emerald-300 text-xs">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-semibold">{stats.approved || 0}</span>
            <span className="text-emerald-400/70">Approved</span>
          </div>

          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-rose-950/40 border border-rose-800/40 text-rose-300 text-xs">
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
            <span className="font-semibold">{stats.rejected || 0}</span>
            <span className="text-rose-400/70">Rejected</span>
          </div>

          <button
            onClick={onOpenAnalytics}
            className="px-3 py-1.5 rounded-lg bg-indigo-900/60 hover:bg-indigo-800 text-indigo-200 border border-indigo-700/60 transition-colors text-xs flex items-center gap-1.5 font-semibold shadow-sm"
          >
            <Network className="w-3.5 h-3.5 text-indigo-400" />
            <span>Graph Analytics & Implications</span>
          </button>

          <button
            onClick={onRefresh}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors text-xs flex items-center gap-1"
            title="Refresh queue"
          >
            <Sparkles className="w-3.5 h-3.5" />
          </button>
        </div>

      </div>
    </header>
  );
}
