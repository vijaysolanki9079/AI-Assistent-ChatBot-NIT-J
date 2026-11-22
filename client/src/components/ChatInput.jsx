import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, MessageSquare } from 'lucide-react';

export default function ChatInput({ onSendMessage, isLoading }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (text.trim() && !isLoading) {
      onSendMessage(text.trim());
      setText('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto resize height with comfortable minimum
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(Math.max(textareaRef.current.scrollHeight, 40), 140)}px`;
    }
  }, [text]);

  return (
    <div className="w-full max-w-5xl mx-auto px-2 sm:px-4">
      <form onSubmit={handleSubmit} className="relative">
        {/* Light-shaded slate text box with prominent borders and visible sided corners */}
        <div className="relative flex items-center light-chat-input rounded-2xl sm:rounded-3xl p-3 sm:p-4 text-slate-100 transition-all duration-300">
          
          {/* Left Visual Icon */}
          <div className="hidden sm:flex items-center pl-1 pr-2 text-purple-400 shrink-0">
            <Sparkles className="w-5 h-5 text-purple-400" />
          </div>

          {/* Text Area */}
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask any placement question (e.g. 'CTC of Microsoft for CSE', 'Top 5 companies by offers', 'Average package CSE vs IT')..."
            rows={1}
            className="w-full bg-transparent text-slate-100 placeholder-slate-400 font-normal text-base sm:text-[16px] px-2 sm:px-3 py-1.5 focus:outline-none resize-none leading-relaxed min-h-[40px]"
            disabled={isLoading}
          />

          {/* Send / Action Button */}
          <div className="flex items-center space-x-2 pl-2 pr-1 shrink-0">
            <button
              type="submit"
              disabled={!text.trim() || isLoading}
              className={`flex items-center justify-center w-11 h-11 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl transition-all duration-200 shadow-md ${
                text.trim() && !isLoading
                  ? 'bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 text-white shadow-purple-600/30 hover:scale-105 active:scale-95 cursor-pointer hover:shadow-lg'
                  : 'bg-white/10 text-slate-500 border border-white/10 cursor-not-allowed'
              }`}
              title="Send question (Enter)"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin text-purple-300" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Bottom Helper Bar */}
        <div className="flex items-center justify-between px-3 pt-2 text-[12px] text-slate-400">
          <span className="flex items-center space-x-1.5">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="font-medium text-slate-300">Strict Zero-Hallucination Policy • Exact Relational Counts Only</span>
          </span>
          <span className="hidden sm:inline-flex items-center space-x-1.5">
            <kbd className="px-2 py-0.5 bg-white/10 border border-white/20 rounded-md font-mono text-[11px] text-slate-300 shadow-sm">Enter ↵</kbd>
            <span className="text-slate-400">to submit</span>
          </span>
        </div>
      </form>
    </div>
  );
}
