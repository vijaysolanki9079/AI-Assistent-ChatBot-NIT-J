import React from 'react';
import { 
  Search, Calculator, BarChart2, Trophy, Percent, 
  TrendingUp, Sliders, AlertOctagon, Briefcase, Sparkles, ShieldAlert, PieChart 
} from 'lucide-react';

const CATEGORIES = [
  { id: "lookup", label: "Lookup", icon: Search, query: "CTC of Microsoft for CSE", color: "from-blue-500/20 to-indigo-500/10 border-blue-500/30 text-blue-300" },
  { id: "count", label: "Count by Condition", icon: Calculator, query: "How many students from IT got placed in Amazon?", color: "from-purple-500/20 to-pink-500/10 border-purple-500/30 text-purple-300" },
  { id: "breakdown", label: "Breakdowns", icon: BarChart2, query: "Company-wise offers for ECE in 2020-2024 batch", color: "from-cyan-500/20 to-blue-500/10 border-cyan-500/30 text-cyan-300" },
  { id: "ranking", label: "Ranking / Top-N", icon: Trophy, query: "Top 5 companies by highest package", color: "from-amber-500/20 to-yellow-500/10 border-amber-500/30 text-amber-300" },
  { id: "aggregates", label: "Aggregates", icon: PieChart, query: "Average CTC of CSE vs IT in 2020-2024 batch", color: "from-emerald-500/20 to-teal-500/10 border-emerald-500/30 text-emerald-300" },
  { id: "percentages", label: "Percentages", icon: Percent, query: "What percentage of CSE students got placed?", color: "from-violet-500/20 to-purple-500/10 border-violet-500/30 text-violet-300" },
  { id: "trends", label: "Trends", icon: TrendingUp, query: "Compare Amazon and Google hiring", color: "from-sky-500/20 to-indigo-500/10 border-sky-500/30 text-sky-300" },
  { id: "multicondition", label: "Multi-condition", icon: Sliders, query: "Companies that hired from both IT and Mechanical Engineering", color: "from-fuchsia-500/20 to-pink-500/10 border-fuchsia-500/30 text-fuchsia-300" },
  { id: "negative", label: "Negative / Zero", icon: AlertOctagon, query: "Which branches were never hired by PayPal?", color: "from-rose-500/20 to-red-500/10 border-rose-500/30 text-rose-300" },
  { id: "offertype", label: "Offer-Type", icon: Briefcase, query: "What is the internship stipend of Microsoft?", color: "from-teal-500/20 to-emerald-500/10 border-teal-500/30 text-teal-300" },
  { id: "hybrid", label: "Hybrid (SQL+RAG)", icon: Sparkles, query: "Which companies gave >18 LPA and what did they ask in interviews?", color: "from-purple-500/30 to-cyan-500/20 border-purple-400 text-purple-200" },
  { id: "guardrail", label: "Privacy Guardrail", icon: ShieldAlert, query: "Who is the HR contact for Amazon?", color: "from-red-500/20 to-orange-500/10 border-red-500/30 text-red-300" }
];

export default function CategoryPills({ onSelectQuery }) {
  return (
    <div className="w-full flex items-center space-x-2 py-2 overflow-x-auto scrollbar-none px-1">
      <div className="flex items-center space-x-1.5 shrink-0 pr-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
        <Sparkles className="w-3.5 h-3.5 text-purple-400" />
        <span className="hidden sm:inline">12 Categories:</span>
      </div>
      <div className="flex items-center space-x-2 shrink-0">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          return (
            <button
              key={cat.id}
              onClick={() => onSelectQuery(cat.query)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-medium border bg-gradient-to-r ${cat.color} hover:brightness-125 transition-all duration-200 shadow-sm whitespace-nowrap active:scale-95`}
              title={`Query: "${cat.query}"`}
            >
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
