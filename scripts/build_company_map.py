import json
import re

with open("scripts/all_raw_companies.json") as f:
    raw_companies = json.load(f)

# Specific manual overrides for known typos / canonical forms
MANUAL_OVERRIDES = {
    "accenutre": "Accenture",
    "accenture": "Accenture",
    "nvida": "Nvidia",
    "nvidia": "Nvidia",
    "intel india": "Intel",
    "intel": "Intel",
    "intel technology india pvt. ltd.": "Intel",
    "microsoft": "Microsoft",
    "microsoft india": "Microsoft",
    "amazon": "Amazon",
    "amazon india": "Amazon",
    "google": "Google",
    "google india": "Google",
    "samsung": "Samsung",
    "samsung sri": "Samsung",
    "samsung r&d": "Samsung",
    "l&t": "L&T",
    "l&t limited": "L&T",
    "l&t ltd.": "L&T",
    "l&t construction": "L&T",
    "larsen & toubro": "L&T",
    "reliance industries limited": "Reliance Industries",
    "reliance industries ltd.": "Reliance Industries",
    "reliance industries ltd": "Reliance Industries",
    "tata consulting engineers limited": "Tata Consulting Engineers",
    "tata consulting engineers ltd.": "Tata Consulting Engineers",
    "tcs": "TCS",
    "tata consultancy services": "TCS",
    "optum": "Optum",
    "optum india": "Optum",
    "cvent": "Cvent",
    "cvent india": "Cvent",
    "cdac": "C-DAC",
    "c-dac": "C-DAC",
    "hero motorcorp": "Hero MotoCorp",
    "hero motor corp": "Hero MotoCorp",
    "heromotocorp": "Hero MotoCorp",
    "future first": "Future First",
    "godigit": "GoDigit",
    "aarti industires limited": "Aarti Industries",
    "aarti industries limited": "Aarti Industries",
    "aakash educational services ltd.": "Aakash Educational Services",
    "aakash education": "Aakash Educational Services",
    "aakash institute": "Aakash Educational Services",
    "allen education": "Allen Career Institute",
    "allen  education": "Allen Career Institute",
    "delhivery limited": "Delhivery",
    "delhivery": "Delhivery",
    "technip energies": "Technip Energies",
    "technipenergies": "Technip Energies",
    "technip energy": "Technip Energies",
    "servicenow india": "ServiceNow",
    "servicenow": "ServiceNow",
    "hcl tech": "HCLTech",
    "hcl tech": "HCLTech",
    "care insurance": "Care Health Insurance",
    "zomato": "Zomato",
    "cadence": "Cadence",
    "cadence design systems": "Cadence",
    "synopsys": "Synopsys",
    "synopsys india": "Synopsys",
    "paypal": "PayPal",
    "paypal university team": "PayPal",
    "dell technology": "Dell Technologies",
    "veritas  technologies": "Veritas Technologies",
    "dayanand sagar university": "Dayananda Sagar University",
    "dayananda sagar university bengaluru": "Dayananda Sagar University",
    "bosch global software technologies pvt. ltd.": "Bosch",
    "bosch": "Bosch"
}

def clean_company_name(raw_name):
    if not raw_name:
        return "Unknown"
    s = raw_name.strip().replace("\n", " ")
    s = re.sub(r'\s+', ' ', s)
    low = s.lower().strip()
    
    if low in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[low]
        
    # Check without trailing punctuation
    low_nopunct = re.sub(r'[\.,]$', '', low).strip()
    if low_nopunct in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[low_nopunct]
        
    # Standard cleanup of corporate suffixes
    cleaned = s
    cleaned = re.sub(r'(?i)\s+(pvt\.?\s*ltd\.?|private\s*limited|ltd\.?|limited|llp|inc\.?)$', '', cleaned).strip()
    cleaned = re.sub(r'(?i)\s+india(\s+pvt\.?\s*ltd\.?)?$', '', cleaned).strip()
    
    low_cleaned = cleaned.lower()
    if low_cleaned in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[low_cleaned]
        
    return cleaned

company_mapping = {}
canonical_set = set()

for raw_name, count in raw_companies.items():
    canon = clean_company_name(raw_name)
    company_mapping[raw_name] = canon
    canonical_set.add(canon)

print(f"Total raw companies: {len(raw_companies)}")
print(f"Total canonical companies after normalization: {len(canonical_set)}")

with open("scripts/company_normalized_map.json", "w") as out:
    json.dump({
        "raw_to_canonical": company_mapping,
        "canonical_count": len(canonical_set),
        "canonical_list": sorted(list(canonical_set))
    }, out, indent=2)

print("Saved company_normalized_map.json")
