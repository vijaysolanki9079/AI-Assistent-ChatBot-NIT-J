import json

with open('eval/baseline_report.json', encoding='utf-8') as f:
    d = json.load(f)

print(f"DEV FAILURES COUNT: {len(d['dev_failures'])}")
for f in d['dev_failures']:
    print(f"  [{f['id']}] Q: \"{f['question']}\"")
    print(f"      Reason: {f['reason']}")
    print(f"      SQL: {f.get('sql')}")
    print(f"      Answer: {f.get('answer_preview')}\n")

print(f"TEMPLATED FAILURES COUNT: {len(d['templated_failures'])}")
for f in d['templated_failures']:
    print(f"  [{f['id']}] Q: \"{f['question']}\"")
    print(f"      Gold: {f.get('gold_count')}, Legacy Payload: {f.get('legacy_payload_count')}\n")

