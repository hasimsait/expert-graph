import React, { useEffect } from 'react';
import { Check, X, ChevronRight, Layers, ExternalLink, ArrowRight, AlertTriangle } from 'lucide-react';

/**
 * EntityNode renders either raw text or a visual mapping to canonical ontology concepts.
 */
function EntityNode({ entity, resolution, label, isSubject }) {
  const isHighConfidence = resolution && resolution.confidence >= 0.80;

  return (
    <div className={`p-4 rounded-2xl border transition-all ${
      isSubject 
        ? 'bg-indigo-950/40 border-indigo-800/60' 
        : 'bg-purple-950/40 border-purple-800/60'
    } flex flex-col justify-between space-y-3`}>
      {/* Node Header Label & Type */}
      <div className="flex items-center justify-between">
        <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full border ${
          isSubject
            ? 'bg-indigo-900/60 text-indigo-300 border-indigo-700/50'
            : 'bg-purple-900/60 text-purple-300 border-purple-700/50'
        }`}>
          {entity?.type || 'ENTITY'}
        </span>
        <span className="text-[10px] text-slate-500 font-mono uppercase tracking-widest font-semibold">
          {label}
        </span>
      </div>

      {/* Node Body: Resolution Mapping or Raw Text */}
      <div className="py-1">
        {resolution ? (
          <div className="flex flex-col items-center gap-2">
            {/* Raw LLM text in muted/gray pill */}
            <div className="flex items-center gap-1.5 flex-wrap justify-center">
              <span className="px-2.5 py-1 rounded-full bg-slate-800/90 text-slate-400 text-xs font-mono border border-slate-700/80">
                {entity?.name}
              </span>
              
              {/* Arrow Icon */}
              <ArrowRight className="w-3.5 h-3.5 text-purple-400 shrink-0" />
            </div>

            {/* Mapped Canonical Name + ID in bold purple pill & Confidence Badge */}
            <div className="flex items-center gap-2 flex-wrap justify-center pt-1">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-900/90 border border-purple-500/70 text-purple-100 font-bold text-xs font-mono shadow-md">
                <span>{resolution.canonical_name}</span>
                <span className="text-purple-300 font-normal text-[11px]">[{resolution.canonical_id}]</span>
              </span>

              {/* Confidence Score Badge */}
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold font-mono border shadow-sm ${
                isHighConfidence
                  ? 'bg-purple-950 text-purple-300 border-purple-600/60'
                  : 'bg-amber-950/90 text-amber-300 border-amber-600/80 animate-pulse'
              }`}>
                {!isHighConfidence && <AlertTriangle className="w-3 h-3 text-amber-400" />}
                <span>{(resolution.confidence * 100).toFixed(0)}%</span>
              </span>
            </div>
          </div>
        ) : (
          /* Raw text fallback when resolution is null */
          <div className="text-center py-2">
            <h3 className="text-base font-bold text-slate-200 font-mono">
              {entity?.name}
            </h3>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * FactCard Component for evaluating pending edges with Entity Resolution metadata.
 */
export default function FactCard({
  currentItem,
  currentIndex = 0,
  totalItems = 0,
  loading = false,
  onApprove,
  onReject,
  onNext,
  feedback = null
}) {
  // Global Keyboard Shortcuts (A: Approve, R: Reject, N: Next/Skip)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (document.activeElement?.tagName === 'TEXTAREA' || document.activeElement?.tagName === 'INPUT') {
        return;
      }
      if (e.key === 'a' || e.key === 'A' || e.key === 'Enter') {
        e.preventDefault();
        onApprove && onApprove();
      } else if (e.key === 'r' || e.key === 'R' || e.key === 'Backspace' || e.key === 'Delete') {
        e.preventDefault();
        onReject && onReject();
      } else if (e.key === 'n' || e.key === 'N' || e.key === 'ArrowRight') {
        e.preventDefault();
        onNext && onNext();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentItem, onApprove, onReject, onNext]);

  return (
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
              {totalItems > 0 && (
                <span className="text-xs font-mono font-normal text-slate-400">
                  ({currentIndex + 1} of {totalItems})
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400">Cross-referenced against Meta-Graph ontology & Entity Resolution</p>
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
            
            {/* Meta-Graph Ontology Lineage if present */}
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

            {/* Triplet Visual Display Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-7 gap-4 items-center bg-slate-950 p-6 rounded-2xl border border-slate-800">
              
              {/* Subject Node (3 cols) */}
              <div className="lg:col-span-3">
                <EntityNode 
                  entity={currentItem.subject} 
                  resolution={currentItem.subject_resolution} 
                  label="Subject" 
                  isSubject={true}
                />
              </div>

              {/* Relation Edge (1 col) */}
              <div className="lg:col-span-1 text-center space-y-2 py-2">
                <div className="inline-block px-3 py-1 rounded-lg bg-indigo-950 border border-indigo-800/80 text-indigo-300 font-mono font-bold text-xs uppercase tracking-wider shadow-sm">
                  {currentItem.relation}
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  Conf: {(currentItem.confidence * 100).toFixed(0)}%
                </div>
              </div>

              {/* Object Node (3 cols) */}
              <div className="lg:col-span-3">
                <EntityNode 
                  entity={currentItem.object} 
                  resolution={currentItem.object_resolution} 
                  label="Object" 
                  isSubject={false}
                />
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
            onClick={onReject}
            className="py-4 px-4 bg-rose-950/80 hover:bg-rose-900 border border-rose-800/80 text-rose-200 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-rose-900/30 group"
          >
            <X className="w-5 h-5 text-rose-400 group-hover:scale-110 transition-transform" />
            <span>Reject (R)</span>
          </button>

          <button
            onClick={onNext}
            className="py-4 px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all"
          >
            <ChevronRight className="w-5 h-5 text-slate-400" />
            <span>Skip (N)</span>
          </button>

          <button
            onClick={onApprove}
            className="py-4 px-4 bg-emerald-600 hover:bg-emerald-500 border border-emerald-500 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-600/20 group"
          >
            <Check className="w-5 h-5 text-white group-hover:scale-110 transition-transform" />
            <span>Approve Fact (A)</span>
          </button>

        </div>
      )}

    </div>
  );
}
