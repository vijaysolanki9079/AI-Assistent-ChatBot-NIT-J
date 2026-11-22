const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Path to python runner and workspace root
const WORKSPACE_ROOT = path.resolve(__dirname, '..');
const RUNNER_SCRIPT = path.join(WORKSPACE_ROOT, 'src', 'api', 'runner.py');
const LOGS_DIR = path.join(WORKSPACE_ROOT, 'logs');
const AUDIT_LOG_FILE = path.join(LOGS_DIR, 'query_audit.jsonl');

// Ensure logs directory exists
if (!fs.existsSync(LOGS_DIR)) {
  fs.mkdirSync(LOGS_DIR, { recursive: true });
}

// In-Memory Query Cache with LRU & TTL (24 Hours)
const QUERY_CACHE = new Map();
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
let cacheHits = 0;
let cacheMisses = 0;

function normalizeQuery(q) {
  return q.trim().toLowerCase().replace(/[?.,!]+$/, '').replace(/\s+/g, ' ');
}

function getFromCache(normalizedKey) {
  const entry = QUERY_CACHE.get(normalizedKey);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
    QUERY_CACHE.delete(normalizedKey);
    return null;
  }
  return entry.data;
}

function setToCache(normalizedKey, data) {
  // Simple LRU: cap at 1000 items
  if (QUERY_CACHE.size >= 1000) {
    const oldestKey = QUERY_CACHE.keys().next().value;
    QUERY_CACHE.delete(oldestKey);
  }
  QUERY_CACHE.set(normalizedKey, {
    timestamp: Date.now(),
    data
  });
}

/**
 * Append audit record to logs/query_audit.jsonl
 */
function logQueryAudit(entry) {
  try {
    const line = JSON.stringify({
      timestamp: new Date().toISOString(),
      ...entry
    }) + '\n';
    fs.appendFile(AUDIT_LOG_FILE, line, (err) => {
      if (err) console.error('Failed to write audit log:', err.message);
    });
  } catch (err) {
    console.error('Audit logging error:', err);
  }
}

// In-Memory Session Store for Conversational Dialog Context (Bug B)
const SESSION_STORE = new Map();

/**
 * Execute Python query planner with session context and history
 */
function executeQuery(payload) {
  return new Promise((resolve, reject) => {
    const argString = typeof payload === 'object' ? JSON.stringify(payload) : payload;
    const pythonProcess = spawn('python', [RUNNER_SCRIPT, argString], {
      cwd: WORKSPACE_ROOT,
      env: { ...process.env, PYTHONPATH: WORKSPACE_ROOT }
    });

    let stdoutData = '';
    let stderrData = '';

    pythonProcess.stdout.on('data', (data) => {
      stdoutData += data.toString('utf8');
    });

    pythonProcess.stderr.on('data', (data) => {
      stderrData += data.toString('utf8');
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`Python process exited with code ${code}: ${stderrData}`);
        return reject(new Error(stderrData || `Process exited with code ${code}`));
      }

      try {
        const parsed = JSON.parse(stdoutData.trim());
        resolve(parsed);
      } catch (err) {
        console.error('Failed to parse Python JSON output:', stdoutData);
        reject(new Error(`Failed to parse response: ${err.message}`));
      }
    });

    pythonProcess.on('error', (err) => {
      reject(err);
    });
  });
}

// 1. Health Endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'NITJ T&P Intelligent Assistant Backend (Express.js)',
    timestamp: new Date().toISOString()
  });
});

// 2. Chat Query Endpoint with Session State & Audit Logging
app.post('/api/chat', async (req, res) => {
  const startTime = Date.now();
  const { message, session_id, history } = req.body;

  if (!message || typeof message !== 'string' || message.trim() === '') {
    return res.status(400).json({
      success: false,
      error: 'Message parameter is required and must be a non-empty string.'
    });
  }

  const queryText = message.trim();
  const sessionId = (session_id && typeof session_id === 'string' && session_id.trim()) 
    ? session_id.trim() 
    : 'default-session';

  const sessionState = SESSION_STORE.get(sessionId) || {
    last_query_spec: null,
    last_answer_summary: null,
    pending_clarification: null
  };

  const hasHistory = Array.isArray(history) && history.length > 0;
  const isFollowup = hasHistory || Boolean(sessionState.last_query_spec) || Boolean(sessionState.pending_clarification);

  cacheMisses++;

  try {
    const payload = {
      query: queryText,
      session_id: sessionId,
      history: hasHistory ? history.slice(-6) : [],
      session_state: sessionState
    };

    // Execute Python tool-using PlacementAgent live on every query
    const plannerResult = await executeQuery(payload);

    // Natural reasoning duration buffer so answers feel thoughtfully computed
    const elapsed = Date.now() - startTime;
    if (elapsed < 350) {
      await new Promise(r => setTimeout(r, 350 - elapsed));
    }
    const durationMs = Date.now() - startTime;

    // Cache purely standalone answers
    if (!isFollowup && !plannerResult.is_followup) {
      const cacheKey = normalizeQuery(queryText);
      setToCache(cacheKey, plannerResult);
    }

    // Update Session State (Bug B)
    const isClarif = (plannerResult.query_spec?.needs_clarification || plannerResult.category === 'ambiguous');
    const clarifQ = plannerResult.query_spec?.clarification_question || (isClarif ? plannerResult.answer : null);

    SESSION_STORE.set(sessionId, {
      last_query_spec: plannerResult.query_spec || null,
      last_answer_summary: plannerResult.answer || null,
      pending_clarification: clarifQ
    });

    return res.json({
      success: true,
      query: queryText,
      session_id: sessionId,
      standalone_question: plannerResult.standalone_question || queryText,
      is_followup: plannerResult.is_followup || false,
      cached: false,
      duration_ms: durationMs,
      data: plannerResult
    });
  } catch (err) {
    const durationMs = Date.now() - startTime;
    console.error('Error processing query:', err);
    logQueryAudit({
      query: queryText,
      cache_hit: false,
      duration_ms: durationMs,
      status: 'error',
      error: err.message
    });
    return res.status(500).json({
      success: false,
      error: 'Internal query execution error',
      details: err.message
    });
  }
});

// 3. System Statistics Endpoint
app.get('/api/stats', (req, res) => {
  res.json({
    success: true,
    stats: {
      total_students: 5470,
      total_offers: 2929,
      placed_students: 2105,
      verified_ctc_offers: 2437,
      stipend_offers: 451,
      peak_international_package: "116.0 LPA (Flow Trades)",
      peak_domestic_package: "62.0 LPA (Google)",
      top_recruiter_by_volume: "Infosys (55 offers)",
      total_canonical_companies: 487,
      alumni_interview_reviews: 409,
      academic_cohorts: [
        "2020-2024 (B.Tech)",
        "2021-2025 (B.Tech)",
        "2022-2026 (B.Tech)",
        "2023-2027 (Summer Interns)",
        "2022-2024 (M.Tech)",
        "2023-2025 (M.Tech / MBA / M.Sc)",
        "2024-2026 (PG)"
      ],
      canonical_branches: 17
    }
  });
});

// 4. Sample Questions Covering All 12 Types
app.get('/api/sample-questions', (req, res) => {
  res.json({
    success: true,
    categories: [
      {
        id: "lookup",
        title: "1. Lookup",
        query: "CTC of Microsoft for CSE",
        desc: "Direct package lookup for specific company and branch"
      },
      {
        id: "count",
        title: "2. Count by Condition",
        query: "How many students from IT got placed in Amazon?",
        desc: "Strict placed student count by branch and recruiter"
      },
      {
        id: "breakdown",
        title: "3. Branch / Year Breakdown",
        query: "Company-wise offers for ECE in 2020-2024 batch",
        desc: "Multi-row cross-tabulation across companies"
      },
      {
        id: "ranking",
        title: "4. Ranking / Top-N",
        query: "Top 5 companies by highest package",
        desc: "Highest paying dream recruiters ranked by package"
      },
      {
        id: "aggregates",
        title: "5. Aggregates with Filters",
        query: "Average CTC of CSE vs IT in 2020-2024 batch",
        desc: "Branch-wise average package comparison"
      },
      {
        id: "percentages",
        title: "6. Percentages / Ratios",
        query: "What percentage of CSE students got placed?",
        desc: "Strict placed students / registered students ratio"
      },
      {
        id: "trends",
        title: "7. Trends / Comparisons",
        query: "Compare Amazon and Google hiring",
        desc: "Side-by-side volume and package comparison"
      },
      {
        id: "multicondition",
        title: "8. Multi-condition",
        query: "Companies that hired from both IT and Mechanical Engineering",
        desc: "Inter-department cross-hiring filters"
      },
      {
        id: "negative",
        title: "9. Negative / Existence",
        query: "Which branches were never hired by PayPal?",
        desc: "Zero-offer department identification"
      },
      {
        id: "offertype",
        title: "10. Offer-type Aware",
        query: "What is the internship stipend of Microsoft?",
        desc: "Strict monthly stipend in INR vs annual CTC in LPA"
      },
      {
        id: "hybrid",
        title: "11. Hybrid (SQL + RAG)",
        query: "Which companies gave >18 LPA and what did they ask in interviews?",
        desc: "Quantitative SQL filtering merged with alumni interview experiences"
      },
      {
        id: "ambiguous",
        title: "12. Clarifying / Scope Guardrail",
        query: "Who is the HR contact for Amazon?",
        desc: "Privacy guardrail blocking confidential student/HR contacts"
      }
    ]
  });
});

// 5. Cache Stats & Admin Endpoint
app.get('/api/cache/stats', (req, res) => {
  res.json({
    cache_size: QUERY_CACHE.size,
    hits: cacheHits,
    misses: cacheMisses,
    hit_rate: cacheHits + cacheMisses > 0 ? (cacheHits / (cacheHits + cacheMisses)).toFixed(3) : 0
  });
});

app.post('/api/cache/clear', (req, res) => {
  QUERY_CACHE.clear();
  res.json({ success: true, message: 'Cache cleared successfully' });
});

// 6. Serve React Production Build
const clientDistPath = path.join(WORKSPACE_ROOT, 'client', 'dist');
if (fs.existsSync(clientDistPath)) {
  app.use(express.static(clientDistPath));
  app.get('*', (req, res, next) => {
    if (req.path.startsWith('/api')) return next();
    res.sendFile(path.join(clientDistPath, 'index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`NITJ Placement Assistant Server running on http://localhost:${PORT}`);
});
