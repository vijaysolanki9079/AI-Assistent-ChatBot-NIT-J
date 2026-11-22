import React from 'react';
import { 
  Sparkles, Trophy, GitCompare, Percent, 
  Search, ShieldCheck, Database, BookOpen, 
  ArrowRight, Briefcase, Award, TrendingUp 
} from 'lucide-react';

const FEATURED_PROMPTS = [
  {
    icon: GitCompare,
    title: "Amazon vs Google Hiring",
    desc: "Compare hiring volumes, average packages, and branch preferences",
    query: "Compare Amazon and Google hiring",
    tag: "Trend Comparison",
    color: "from-blue-500/20 to-indigo-500/10 text-blue-300 border-blue-500/30"
  },
  {
    icon: Trophy,
    title: "Top 5 Highest Packages",
    desc: "Discover dream offers, peak domestic and international compensation",
    query: "Top 5 companies by highest package",
    tag: "Ranking",
    color: "from-amber-500/20 to-yellow-500/10 text-amber-300 border-amber-500/30"
  },
  {
    icon: Sparkles,
    title: "Companies > 18 LPA + Interview Qs",
    desc: "Hybrid relational SQL + alumni interview experience questions",
    query: "Which companies gave >18 LPA and what did they ask in interviews?",
    tag: "Hybrid SQL + RAG",
    color: "from-purple-500/20 to-pink-500/10 text-purple-300 border-purple-500/30"
  },
  {
    icon: Percent,
    title: "CSE vs IT Placement Rate",
    desc: "Evaluate placed student percentages and batch conversion rates",
    query: "What percentage of CSE students got placed?",
    tag: "Percentages",
    color: "from-emerald-500/20 to-teal-500/10 text-emerald-300 border-emerald-500/30"
  },
  {
    icon: Search,
    title: "Zero-Offer Branches for PayPal",
    desc: "Negative relational query identifying departments never visited",
    query: "Which branches were never hired by PayPal?",
    tag: "Negative Query",
    color: "from-rose-500/20 to-red-500/10 text-rose-300 border-rose-500/30"
  },
  {
    icon: Briefcase,
    title: "Internship Stipend vs CTC",
    desc: "Strict distinction between monthly stipend (INR) and annual CTC (LPA)",
    query: "What is the internship stipend of Microsoft?",
    tag: "Offer-Type Aware",
    color: "from-cyan-500/20 to-sky-500/10 text-cyan-300 border-cyan-500/30"
  }
];

export default function HeroSection({ onSelectPrompt, stats }) {
  return (
    <div className="w-full flex flex-col items-center justify-center pt-4 pb-8 space-y-8 animate-fadeIn">
      {/* Official Institutional Badge */}
      <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-xl shadow-lg">
        <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-xs font-medium text-slate-300">
          NIT Jalandhar Training & Placement Division
        </span>
        <span className="text-slate-600">•</span>
        <span className="text-[11px] font-semibold text-purple-400 uppercase tracking-wider">
          Zero-Hallucination Engine
        </span>
      </div>

      {/* Hero Headline */}
      <div className="text-center max-w-3xl space-y-3 px-4">
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
          Precision Placement{' '}
          <span className="bg-gradient-to-r from-cyan-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
            Intelligence
          </span>
        </h1>
        <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Ask complex placement questions, compare companies, evaluate branch trends, and retrieve verified alumni interview experiences with mathematical certainty.
        </p>
      </div>

      {/* Floating Key Metrics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 w-full max-w-5xl px-2">
        <div className="glass-panel p-4 rounded-2xl flex flex-col items-center justify-center text-center border-2 border-white/15 hover:border-purple-500/40 shadow-xl transition-all">
          <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-mono">
            {stats?.total_students ? stats.total_students.toLocaleString() : '5,470'}
          </span>
          <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider mt-1">
            Registered Candidates
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl flex flex-col items-center justify-center text-center border-2 border-white/15 hover:border-purple-500/40 shadow-xl transition-all">
          <span className="text-2xl sm:text-3xl font-extrabold text-purple-300 tracking-tight font-mono">
            {stats?.total_offers ? stats.total_offers.toLocaleString() : '2,929'}
          </span>
          <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider mt-1">
            Placement Offers
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl flex flex-col items-center justify-center text-center border-2 border-white/15 hover:border-purple-500/40 shadow-xl transition-all">
          <span className="text-2xl sm:text-3xl font-extrabold text-cyan-300 tracking-tight font-mono">
            116.0 LPA
          </span>
          <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider mt-1">
            Peak International CTC
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl flex flex-col items-center justify-center text-center border-2 border-white/15 hover:border-purple-500/40 shadow-xl transition-all">
          <span className="text-2xl sm:text-3xl font-extrabold text-emerald-300 tracking-tight font-mono">
            {stats?.alumni_interview_reviews || '409'}
          </span>
          <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider mt-1">
            Alumni Reviews (RAG)
          </span>
        </div>
      </div>

      {/* Featured Starter Prompts Grid */}
      <div className="w-full max-w-5xl space-y-3.5 px-2">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>Popular Inquiries (Click to Ask)</span>
          </span>
          <span className="text-[11px] text-slate-500 font-medium">12 Deterministic Categories</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {FEATURED_PROMPTS.map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={idx}
                onClick={() => onSelectPrompt(item.query)}
                className="group relative text-left p-4 sm:p-5 rounded-2xl glass-panel border-2 border-white/15 hover:border-purple-500/50 hover:bg-white/[0.08] transition-all duration-300 flex flex-col justify-between space-y-3.5 shadow-xl hover:shadow-purple-500/20 hover:-translate-y-0.5 cursor-pointer"
              >
                <div className="flex items-start justify-between">
                  <div className={`p-2 rounded-xl bg-gradient-to-br ${item.color} border`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 px-2 py-0.5 rounded-full bg-white/5 border border-white/10">
                    {item.tag}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-200 group-hover:text-white transition-colors">
                    {item.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {item.desc}
                  </p>
                </div>

                <div className="flex items-center text-xs font-medium text-purple-400 group-hover:text-purple-300 pt-1">
                  <span>Run query</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1 transition-transform group-hover:translate-x-1" />
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

