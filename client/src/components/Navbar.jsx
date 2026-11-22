import React from 'react';
import { Sparkles, BarChart3, RotateCcw, ShieldCheck, Database, GraduationCap } from 'lucide-react';

export default function Navbar({ onOpenStats, onResetChat, totalOffers = 2929, totalExps = 409 }) {
  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-white/10 px-4 sm:px-8 py-3 backdrop-blur-2xl bg-[#07090e]/85">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        {/* Brand identity */}
        <div className="flex items-center space-x-3.5">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-400 p-[1.5px] shadow-lg shadow-purple-500/25">
            <div className="w-full h-full bg-[#0a0d17] rounded-xl flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-purple-300" />
            </div>
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm sm:text-base font-bold tracking-tight text-white">
                NIT Jalandhar T&P Assistant
              </h1>
              <span className="hidden sm:inline-flex items-center space-x-1 px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 rounded-full">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                <span>Zero Hallucination</span>
              </span>
            </div>
            <p className="text-[11px] text-slate-400 flex items-center space-x-1.5 mt-0.5">
              <span>Verified Relational Placement SQL</span>
              <span className="text-slate-600">•</span>
              <span className="text-cyan-400">pgvector Alumni RAG</span>
            </p>
          </div>
        </div>

        {/* Quick actions & stats */}
        <div className="flex items-center space-x-2">
          <button
            onClick={onOpenStats}
            className="flex items-center space-x-2 px-3 py-1.5 text-xs font-medium text-slate-300 bg-white/5 hover:bg-white/10 hover:text-white border border-white/10 hover:border-purple-500/40 rounded-xl transition-all duration-200 shadow-sm"
            title="View Database Statistics"
          >
            <BarChart3 className="w-4 h-4 text-purple-400" />
            <span className="hidden sm:inline">Database Stats</span>
          </button>

          <button
            onClick={onResetChat}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all duration-200"
            title="Reset Conversation"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Reset</span>
          </button>
        </div>
      </div>
    </header>
  );
}
