import React from 'react';
import { X, Users, Award, TrendingUp, Building2, BookOpen, Layers, CheckCircle2 } from 'lucide-react';

export default function StatsModal({ isOpen, onClose, stats }) {
  if (!isOpen) return null;

  const cards = [
    { label: "Total Students", val: stats.total_students?.toLocaleString() || "5,470", icon: Users, color: "from-blue-500/20 to-indigo-500/10", border: "border-blue-500/30", text: "text-blue-400" },
    { label: "Total Offers", val: stats.total_offers?.toLocaleString() || "2,929", icon: Award, color: "from-purple-500/20 to-pink-500/10", border: "border-purple-500/30", text: "text-purple-400" },
    { label: "Distinct Placed", val: stats.placed_students?.toLocaleString() || "2,105", icon: CheckCircle2, color: "from-emerald-500/20 to-teal-500/10", border: "border-emerald-500/30", text: "text-emerald-400" },
    { label: "Recruiting Companies", val: stats.total_canonical_companies || "487", icon: Building2, color: "from-cyan-500/20 to-blue-500/10", border: "border-cyan-500/30", text: "text-cyan-400" },
    { label: "Peak Package (Intl)", val: stats.peak_international_package || "116.0 LPA", icon: TrendingUp, color: "from-amber-500/20 to-orange-500/10", border: "border-amber-500/30", text: "text-amber-400" },
    { label: "Alumni Experiences", val: stats.alumni_interview_reviews || "409", icon: BookOpen, color: "from-rose-500/20 to-red-500/10", border: "border-rose-500/30", text: "text-rose-400" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl glass-panel border border-white/15 rounded-3xl p-6 sm:p-8 shadow-2xl overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-purple-600/30 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-cyan-600/20 rounded-full blur-3xl pointer-events-none" />

        {/* Modal Header */}
        <div className="flex items-center justify-between pb-5 border-b border-white/10">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2">
              <span>Verified Database Statistics</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Source: NIT Jalandhar Training & Placement Database (Cleaned Schema)
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Metric Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3.5 my-6">
          {cards.map((c, i) => {
            const Icon = c.icon;
            return (
              <div
                key={i}
                className={`p-4 rounded-2xl bg-gradient-to-br ${c.color} border ${c.border} backdrop-blur-sm`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400 font-medium">{c.label}</span>
                  <Icon className={`w-4 h-4 ${c.text}`} />
                </div>
                <div className="text-lg sm:text-xl font-bold text-white tracking-tight">
                  {c.val}
                </div>
              </div>
            );
          })}
        </div>

        {/* Cohort Coverage */}
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
          <div className="flex items-center space-x-2 mb-2">
            <Layers className="w-4 h-4 text-purple-400" />
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Academic Cohorts Covered
            </h4>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-slate-300">
            {stats.academic_cohorts?.map((coh, idx) => (
              <span key={idx} className="px-2.5 py-1 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                {coh}
              </span>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-purple-600/30 transition-all duration-200"
          >
            Close Overview
          </button>
        </div>
      </div>
    </div>
  );
}

