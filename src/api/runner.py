import sys
import os
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from src.agent.agent import PlacementAgent

def main():
    agent = PlacementAgent()

    # If argument provided, run single query
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.startswith("{") and arg.endswith("}"):
            try:
                payload = json.loads(arg)
                query_text = payload.get("query") or payload.get("message") or ""
                history = payload.get("history") or []
                session_state = payload.get("session_state") or {}
                result = agent.plan_and_execute(query_text, history=history, session_state=session_state)
                print(json.dumps(result, ensure_ascii=False))
                return
            except Exception:
                pass
        result = agent.plan_and_execute(arg)
        print(json.dumps(result, ensure_ascii=False))
        return

    # Otherwise listen for JSON lines on stdin (persistent mode for Express backend)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            q = req.get("query") or req.get("message") or ""
            history = req.get("history") or []
            session_state = req.get("session_state") or {}
            result = agent.plan_and_execute(q, history=history, session_state=session_state)
            print(json.dumps(result, ensure_ascii=False), flush=True)
        except Exception as e:
            err_res = {
                "category": "out_of_scope",
                "answer": "We don't have records for this in our placement database right now. Our Training & Placement team is actively working on gathering and updating this data, and we'll fix it soon!",
                "confidence": "Low",
                "assumptions": "Error handling recovery"
            }
            print(json.dumps(err_res, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
