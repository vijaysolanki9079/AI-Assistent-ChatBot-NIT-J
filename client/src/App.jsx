import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import StatsModal from './components/StatsModal';
import CategoryPills from './components/CategoryPills';
import StrictAnswerView from './components/StrictAnswerView';
import ChatInput from './components/ChatInput';
import HeroSection from './components/HeroSection';
import { 
  Bot, User, Sparkles, AlertTriangle, ShieldCheck, 
  HelpCircle, CheckCircle, Database 
} from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught rendering error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/25 text-amber-200 space-y-2">
          <div className="font-semibold text-amber-300 text-sm">Response Rendering Safe Mode</div>
          <p className="text-xs text-slate-300">A display issue was safely caught. The answer is preserved below:</p>
          <div className="text-xs text-slate-200 font-mono bg-black/40 p-2.5 rounded-lg border border-white/5">
            {String(this.state.error?.message || 'Rendering recovered')}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStatsOpen, setIsStatsOpen] = useState(false);
  const [stats, setStats] = useState({
    total_students: 5470,
    total_offers: 2929,
    placed_students: 2105,
    verified_ctc_offers: 2437,
    stipend_offers: 451,
    peak_international_package: "116.0 LPA (Flow Trades)",
    peak_domestic_package: "62.0 LPA (Google)",
    total_canonical_companies: 487,
    alumni_interview_reviews: 409,
    academic_cohorts: [
      "2020-2024 (B.Tech)", "2021-2025 (B.Tech)", "2022-2026 (B.Tech)",
      "2023-2027 (Summer Interns)", "2022-2024 (M.Tech)", "2023-2025 (PG)"
    ]
  });

  const chatBottomRef = useRef(null);
  
  // Persistent session ID for multi-turn dialogs (Bug B)
  const sessionIdRef = useRef(null);
  if (!sessionIdRef.current) {
    sessionIdRef.current = (typeof crypto !== 'undefined' && crypto.randomUUID) 
      ? crypto.randomUUID() 
      : `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }

  // Fetch institutional stats on mount
  useEffect(() => {
    fetch('/api/stats')
      .then(res => res.json())
      .then(data => {
        if (data.success && data.stats) {
          setStats(data.stats);
        }
      })
      .catch(err => console.warn('Using local fallback stats:', err));
  }, []);

  // Scroll to bottom on messages update
  useEffect(() => {
    if (messages.length > 0) {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  const handleSendMessage = async (queryText) => {
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: queryText
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      // Send last 6 messages as history
      const recentHistory = messages.slice(-6).map(m => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.sender === 'user' ? m.text : (m.content?.answer || '')
      }));

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: queryText,
          session_id: sessionIdRef.current,
          history: recentHistory
        })
      });

      const json = await response.json();

      if (json.success && json.data) {
        const assistantMsg = {
          id: `bot-${Date.now()}`,
          sender: 'assistant',
          content: json.data,
          cached: json.cached,
          duration_ms: json.duration_ms
        };
        setMessages(prev => [...prev, assistantMsg]);
      } else {
        const errorMsg = {
          id: `bot-err-${Date.now()}`,
          sender: 'assistant',
          content: {
            answer: json.error || "We don't have records for this in our placement database right now. Our Training & Placement team is actively working on gathering and updating this data, and we'll have it added soon!",
            data_scope: "Records currently unavailable",
            confidence: "Database Notice",
            category: "out_of_scope",
            insight: json.details || "Try asking about companies like Google, Microsoft, Amazon, or branches like CSE, ECE, IT."
          }
        };
        setMessages(prev => [...prev, errorMsg]);
      }
    } catch (err) {
      console.error('API Error:', err);
      const networkErrorMsg = {
        id: `bot-neterr-${Date.now()}`,
        sender: 'assistant',
        content: {
          answer: "Connection error: Unable to reach the Express.js query backend.",
          data_scope: "Network error",
          confidence: "Low",
          insight: "Ensure the Node.js / Express backend is running on port 5000."
        }
      };
      setMessages(prev => [...prev, networkErrorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetChat = () => {
    setMessages([]);
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between selection:bg-purple-500 selection:text-white">
      {/* Animated Liquid Background Orbs */}
      <div className="liquid-bg">
        <div className="liquid-orb orb-1" />
        <div className="liquid-orb orb-2" />
        <div className="liquid-orb orb-3" />
      </div>

      {/* Top Navbar */}
      <Navbar
        onOpenStats={() => setIsStatsOpen(true)}
        onResetChat={handleResetChat}
        totalOffers={stats.total_offers}
        totalExps={stats.alumni_interview_reviews}
      />

      {/* Database Statistics Modal */}
      <StatsModal
        isOpen={isStatsOpen}
        onClose={() => setIsStatsOpen(false)}
        stats={stats}
      />

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 py-4 flex flex-col justify-start">
        {/* Category Carousel Pills */}
        <div className="mb-4">
          <CategoryPills onSelectQuery={handleSendMessage} />
        </div>

        {/* Empty State / Hero Section */}
        {messages.length === 0 ? (
          <HeroSection onSelectPrompt={handleSendMessage} stats={stats} />
        ) : (
          /* Conversational Message Stream */
          <div className="flex-1 space-y-6 pb-6">
            {messages.map((msg, index) => (
              <div
                key={msg.id}
                className={`flex items-start space-x-3 ${
                  msg.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.sender === 'assistant' && (
                  <div className="w-9 h-9 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-400 p-[1.5px] shadow-lg shadow-purple-600/25 shrink-0 mt-1">
                    <div className="w-full h-full bg-[#0a0d17] rounded-2xl flex items-center justify-center">
                      <Bot className="w-4 h-4 text-purple-300" />
                    </div>
                  </div>
                )}

                <div
                  className={`transition-all duration-300 ${
                    msg.sender === 'user'
                      ? 'max-w-2xl rounded-2xl rounded-tr-none px-5 py-3.5 bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-700 text-white shadow-xl shadow-purple-600/25 text-[15px] font-medium leading-relaxed border-2 border-indigo-400/40'
                      : 'w-full max-w-5xl glass-panel border-2 border-white/15 hover:border-purple-500/40 shadow-2xl rounded-2xl sm:rounded-3xl p-5 sm:p-6'
                  }`}
                >
                  {msg.sender === 'user' ? (
                    <p>{msg.text}</p>
                  ) : (
                    <ErrorBoundary>
                      <StrictAnswerView 
                        data={msg.content} 
                        isLatest={index === messages.length - 1 && msg.sender === 'assistant'} 
                      />
                    </ErrorBoundary>
                  )}
                </div>

                {msg.sender === 'user' && (
                  <div className="w-9 h-9 rounded-2xl bg-white/10 border border-white/15 flex items-center justify-center shrink-0 mt-1 shadow-md">
                    <User className="w-4 h-4 text-purple-300" />
                  </div>
                )}
              </div>
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex items-start space-x-3">
                <div className="w-9 h-9 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-400 p-[1.5px] shadow-lg shadow-purple-600/25 shrink-0 mt-1 animate-pulse">
                  <div className="w-full h-full bg-[#0a0d17] rounded-2xl flex items-center justify-center">
                    <Bot className="w-4 h-4 text-purple-300" />
                  </div>
                </div>
                <div className="glass-panel border border-white/10 rounded-2xl px-5 py-3.5 flex items-center space-x-3 shadow-xl">
                  <div className="flex space-x-1.5">
                    <div className="w-2 h-2 rounded-full bg-purple-400 animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce"></div>
                  </div>
                  <span className="text-xs text-slate-300 font-medium">
                    Formulating relational SQL & querying alumni RAG...
                  </span>
                </div>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>
        )}
      </main>

      {/* Sticky Bottom Input Bar */}
      <footer className="sticky bottom-0 z-30 w-full px-2 sm:px-4 py-3.5 bg-gradient-to-t from-[#07090e] via-[#07090e]/95 to-transparent backdrop-blur-md">
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </footer>
    </div>
  );
}
