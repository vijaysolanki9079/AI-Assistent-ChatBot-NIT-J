import React, { useState, useEffect } from 'react';
import { 
  Check, Copy, Database, Code2, Sparkles, BookOpen, 
  User, Calendar, Lightbulb, ShieldCheck, HelpCircle, 
  Info, Table as TableIcon, Search
} from 'lucide-react';

export default function StrictAnswerView({ data, isLatest = false }) {
  const [copiedSQL, setCopiedSQL] = useState(false);
  const [tableSearch, setTableSearch] = useState('');
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  if (!data) return null;

  const {
    answer,
    table,
    insight,
    definition,
    data_scope,
    confidence,
    sql,
    category,
    raw_result,
    rag_results,
    citations
  } = data;

  const fullAnswer = typeof answer === 'string' ? answer : (answer ? String(answer) : '');

  // Typewriter streaming effect for fresh incoming assistant responses
  useEffect(() => {
    if (!isLatest || !fullAnswer) {
      setDisplayedText(fullAnswer);
      setIsTyping(false);
      return;
    }

    setIsTyping(true);
    setDisplayedText('');
    
    // Split text by words and whitespace tokens
    const tokens = fullAnswer.split(/(\s+)/);
    let index = 0;
    let accumulated = '';

    const interval = setInterval(() => {
      if (index < tokens.length) {
        accumulated += tokens[index];
        setDisplayedText(accumulated);
        index++;
      } else {
        clearInterval(interval);
        setIsTyping(false);
      }
    }, 18); // Natural streaming pace (approx 50 words/sec)

    return () => clearInterval(interval);
  }, [fullAnswer, isLatest]);

  const copySQL = () => {
    if (sql) {
      navigator.clipboard.writeText(sql);
      setCopiedSQL(true);
      setTimeout(() => setCopiedSQL(false), 2000);
    }
  };

  // Safe table parser: handles object format { columns, rows }, markdown string, or arrays
  const parseTable = (tbl) => {
    if (!tbl) return null;
    try {
      // 1. Structured analytical object format from PlacementAgent
      if (typeof tbl === 'object' && !Array.isArray(tbl)) {
        const headers = tbl.columns || tbl.headers || [];
        const rows = tbl.rows || [];
        if (Array.isArray(headers) && headers.length > 0 && Array.isArray(rows)) {
          return {
            headers: headers.map(h => String(h || '').replace(/_/g, ' ')),
            rows: rows.map(r => Array.isArray(r) ? r.map(c => String(c ?? '')) : [String(r ?? '')])
          };
        }
      }
      // 2. Markdown string format
      if (typeof tbl === 'string') {
        const lines = tbl.trim().split('\n').filter(l => l.trim().startsWith('|'));
        if (lines.length < 2) return null;
        const headers = lines[0].split('|').map(c => c.trim()).filter(Boolean);
        const rows = lines.slice(2).map(line => {
          return line.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
        });
        return { headers, rows };
      }
      // 3. Array of objects format
      if (Array.isArray(tbl) && tbl.length > 0 && typeof tbl[0] === 'object') {
        const headers = Object.keys(tbl[0]);
        const rows = tbl.map(row => headers.map(h => String(row[h] ?? '')));
        return { headers, rows };
      }
    } catch (err) {
      console.warn('Table parsing error:', err);
    }
    return null;
  };

  const parsedTable = parseTable(table);

  // Filter table rows if search term provided
  const filteredRows = parsedTable ? parsedTable.rows.filter(r => 
    r.some(cell => cell.toLowerCase().includes(tableSearch.toLowerCase()))
  ) : [];

  // Filter out trivial robotic insights
  const isMeaningfulInsight = (txt) => {
    if (!txt || typeof txt !== 'string') return false;
    const low = txt.toLowerCase().trim();
    if (
      low.startsWith('total count:') || 
      low.startsWith('calculated single aggregate:') || 
      (low.startsWith('includes') && low.includes('entries across the selected dimensions'))
    ) {
      return false;
    }
    return true;
  };

  // High quality inline formatting: bold, code, highlights
  const renderInline = (str) => {
    if (!str) return null;
    const tokens = str.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return tokens.map((tok, i) => {
      if (tok.startsWith('**') && tok.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-white tracking-wide">
            {tok.slice(2, -2)}
          </strong>
        );
      }
      if (tok.startsWith('`') && tok.endsWith('`')) {
        return (
          <code key={i} className="px-1.5 py-0.5 rounded-md bg-white/10 text-purple-300 font-mono text-xs border border-white/5">
            {tok.slice(1, -1)}
          </code>
        );
      }
      return tok;
    });
  };

  // Block formatter: paragraphs, bullet points, numbered lists
  const renderFormattedContent = (content) => {
    if (!content) return null;
    const lines = content.split('\n');
    const elements = [];
    let currentBullets = [];

    const flushBullets = () => {
      if (currentBullets.length > 0) {
        elements.push(
          <div key={`bullets-${elements.length}`} className="my-2.5 space-y-2 pl-1">
            {currentBullets.map((b, bIdx) => (
              <div key={bIdx} className="flex items-start space-x-3 text-[14px] leading-relaxed text-slate-200">
                <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-purple-400 to-cyan-400 mt-2 shrink-0 shadow-sm shadow-purple-500/50" />
                <div className="flex-1">{renderInline(b)}</div>
              </div>
            ))}
          </div>
        );
        currentBullets = [];
      }
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) {
        flushBullets();
        return;
      }

      // Bullet check (•, -, *)
      if (trimmed.startsWith('•') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const bulletText = trimmed.replace(/^[•\-\*]\s*/, '');
        currentBullets.push(bulletText);
      } else {
        flushBullets();
        elements.push(
          <p key={`p-${idx}`} className="text-[14.5px] leading-relaxed text-slate-200 my-1 font-normal">
            {renderInline(trimmed)}
          </p>
        );
      }
    });

    flushBullets();
    return elements;
  };

  // Determine special banner states
  const textToCheck = displayedText || fullAnswer;
  const isNoData = 
    category === 'out_of_scope' || 
    raw_result === 'NO_DATA' || 
    raw_result === 'OUT_OF_SCOPE' ||
    (textToCheck && (textToCheck.toLowerCase().includes('database right now') || textToCheck.toLowerCase().includes('working on')));

  const isPrivacy = 
    category === 'privacy' || 
    category === 'privacy_refusal' ||
    raw_result === 'PRIVACY_BLOCKED';

  const isClarification = 
    category === 'ambiguous' || 
    raw_result === 'CLARIFICATION_REQUIRED';

  const citationDocs = citations || rag_results || [];

  return (
    <div className="space-y-4 text-slate-100 text-sm leading-relaxed">
      {/* 1. STATE CARDS (NO DATA / PRIVACY / CLARIFICATION) OR NATURAL CHAT ANSWER */}
      {isNoData ? (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border border-amber-500/25 shadow-xl backdrop-blur-md space-y-2.5">
          <div className="flex items-center space-x-2.5 text-amber-300 font-semibold text-xs tracking-wider uppercase">
            <div className="w-6 h-6 rounded-lg bg-amber-500/20 flex items-center justify-center border border-amber-500/30">
              <Database className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <span>Placement Database Notice</span>
          </div>
          <div className="text-[14.5px] leading-relaxed text-slate-200">
            {renderFormattedContent(displayedText)}
            {isTyping && (
              <span className="inline-block w-2 h-4 ml-1.5 bg-gradient-to-b from-amber-400 to-purple-400 animate-pulse rounded-sm align-middle shadow-sm shadow-amber-500/50" />
            )}
          </div>
          <div className="pt-2 border-t border-amber-500/15 flex items-center space-x-2 text-xs text-amber-200/70">
            <Info className="w-3.5 h-3.5 shrink-0 text-amber-400" />
            <span>Tip: Try querying recruiters like Google, Microsoft, Amazon, or branches like CSE, ECE, IT.</span>
          </div>
        </div>
      ) : isPrivacy ? (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-purple-500/10 via-indigo-500/5 to-transparent border border-purple-500/25 shadow-xl backdrop-blur-md space-y-2.5">
          <div className="flex items-center space-x-2.5 text-purple-300 font-semibold text-xs tracking-wider uppercase">
            <div className="w-6 h-6 rounded-lg bg-purple-500/20 flex items-center justify-center border border-purple-500/30">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <span>Student Privacy Protected</span>
          </div>
          <div className="text-[14.5px] leading-relaxed text-slate-200">
            {renderFormattedContent(displayedText)}
            {isTyping && (
              <span className="inline-block w-2 h-4 ml-1.5 bg-gradient-to-b from-purple-400 to-indigo-400 animate-pulse rounded-sm align-middle shadow-sm shadow-purple-500/50" />
            )}
          </div>
        </div>
      ) : isClarification ? (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-indigo-500/10 via-blue-500/5 to-transparent border border-indigo-500/25 shadow-xl backdrop-blur-md space-y-2.5">
          <div className="flex items-center space-x-2.5 text-indigo-300 font-semibold text-xs tracking-wider uppercase">
            <div className="w-6 h-6 rounded-lg bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
              <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
            </div>
            <span>Clarification Needed</span>
          </div>
          <div className="text-[14.5px] leading-relaxed text-slate-200">
            {renderFormattedContent(displayedText)}
            {isTyping && (
              <span className="inline-block w-2 h-4 ml-1.5 bg-gradient-to-b from-indigo-400 to-cyan-400 animate-pulse rounded-sm align-middle shadow-sm shadow-indigo-500/50" />
            )}
          </div>
        </div>
      ) : (
        <div className="text-slate-100 text-[14.5px] leading-relaxed space-y-2">
          {renderFormattedContent(displayedText)}
          {isTyping && (
            <span className="inline-block w-2 h-4 ml-1.5 bg-gradient-to-b from-purple-400 to-cyan-400 animate-pulse rounded-sm align-middle shadow-sm shadow-purple-500/50" />
          )}
        </div>
      )}

      {/* 2. RESULT TABLE (IF MULTI-ROW TABULAR RESULT) */}
      {!isTyping && parsedTable && parsedTable.headers.length > 0 && (
        <div className="my-3.5 rounded-2xl border border-white/10 bg-slate-950/80 overflow-hidden shadow-2xl backdrop-blur-md">
          <div className="flex items-center justify-between px-4 py-2.5 bg-white/[0.03] border-b border-white/10">
            <div className="flex items-center space-x-2 text-xs font-semibold text-purple-300">
              <TableIcon className="w-4 h-4 text-purple-400" />
              <span>Placement Breakdown ({parsedTable.rows.length} records)</span>
            </div>
            {parsedTable.rows.length > 5 && (
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search records..."
                  value={tableSearch}
                  onChange={(e) => setTableSearch(e.target.value)}
                  className="pl-8 pr-3 py-1 text-xs bg-slate-900/90 border border-white/10 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
              </div>
            )}
          </div>
          <div className="overflow-x-auto max-h-72 scrollbar-none">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="bg-slate-900/95 border-b border-white/10 sticky top-0 backdrop-blur-md">
                  {parsedTable.headers.map((h, idx) => (
                    <th key={idx} className="px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wider text-purple-300">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredRows.length > 0 ? (
                  filteredRows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-purple-500/10 transition-colors">
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-4 py-2 text-slate-200">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={parsedTable.headers.length} className="px-4 py-6 text-center text-slate-500">
                      No matching records found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. MEANINGFUL INSIGHT */}
      {!isTyping && isMeaningfulInsight(insight) && (
        <div className="flex items-start space-x-2 pt-1 text-xs text-slate-300">
          <Lightbulb className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <span className="leading-relaxed">{renderInline(insight)}</span>
        </div>
      )}

      {/* 4. ALUMNI INTERVIEW EXPERIENCES / CITATIONS */}
      {!isTyping && citationDocs.length > 0 && (
        <div className="mt-3.5 pt-3 space-y-2.5 border-t border-white/5">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-cyan-300">
            <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
            <span>Alumni Interview Verified Citations ({citationDocs.length} records)</span>
          </div>

          <div className="space-y-2.5 pt-1">
            {citationDocs.map((doc, idx) => (
              <div key={idx} className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10 text-xs space-y-1.5 hover:border-purple-500/30 transition-colors">
                <div className="flex items-center justify-between font-semibold">
                  <span className="text-purple-300 text-sm">{doc.company || 'Alumni Review'}</span>
                  <span className="text-[10px] text-slate-400 flex items-center space-x-2">
                    {doc.batch && <span className="bg-white/5 px-2 py-0.5 rounded border border-white/10">{doc.batch}</span>}
                    {doc.source && <span className="text-cyan-300/80">{doc.source}</span>}
                  </span>
                </div>
                {doc.role && <div className="text-slate-400 italic">Role: {doc.role}</div>}
                {doc.key_questions && doc.key_questions.length > 0 && (
                  <div className="text-[11px] text-amber-200/90 bg-amber-500/10 p-2.5 rounded-lg border border-amber-500/20">
                    <span className="font-semibold block mb-1">Sample Questions Asked:</span>
                    <ul className="list-disc list-inside space-y-0.5">
                      {doc.key_questions.slice(0, 3).map((q, qIdx) => (
                        <li key={qIdx}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {doc.excerpt && (
                  <p className="text-slate-300 leading-relaxed text-[11px] pt-0.5">
                    {doc.excerpt}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. COLLAPSIBLE FOOTER FOR DEVELOPER/AUDIT DETAILS */}
      {!isTyping && (sql || definition || data.assumptions) && (
        <details className="mt-3 pt-2 border-t border-white/5 group text-xs text-slate-400">
          <summary className="cursor-pointer inline-flex items-center space-x-1.5 py-1 px-2.5 rounded-lg bg-white/5 hover:bg-white/10 hover:text-slate-200 border border-white/5 transition-all select-none">
            <Code2 className="w-3.5 h-3.5 text-purple-400" />
            <span>View SQL query & verified scope</span>
          </summary>

          <div className="mt-2.5 p-3.5 rounded-xl bg-black/60 border border-white/10 space-y-2.5 font-mono text-[11px] shadow-inner">
            {sql && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-slate-300 font-semibold">Generated Analytical SQL Query:</span>
                  <button
                    onClick={copySQL}
                    className="text-purple-300 hover:text-white flex items-center space-x-1 bg-white/5 px-2 py-0.5 rounded transition-colors"
                  >
                    {copiedSQL ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedSQL ? 'Copied' : 'Copy SQL'}</span>
                  </button>
                </div>
                <pre className="text-purple-200 overflow-x-auto p-2.5 bg-[#080b13] border border-white/5 rounded-lg whitespace-pre-wrap leading-relaxed">
                  {sql}
                </pre>
              </div>
            )}

            {data.assumptions && (
              <div className="text-slate-300">
                <span className="text-indigo-300 font-semibold">Scope / Assumptions:</span> {data.assumptions}
              </div>
            )}

            {definition && (
              <div className="text-slate-300">
                <span className="text-purple-300 font-semibold">Metric Rule:</span> {definition}
              </div>
            )}

            {data_scope && (
              <div className="text-slate-300">
                <span className="text-indigo-300 font-semibold">Data Scope:</span> {data_scope}
              </div>
            )}

            {confidence && (
              <div className="text-slate-300">
                <span className="text-emerald-300 font-semibold">Verification:</span> {confidence}
              </div>
            )}
          </div>
        </details>
      )}
    </div>
  );
}
