"""LeaseCheck core logic: read a lease, check it against rules.json, return findings.

Two modes:
  - AI mode (needs ANTHROPIC_API_KEY): Claude reads the lease and matches clauses to the rules.
  - Demo mode (no key): simple keyword matching so the team can test the app without an API key.
"""

import io
import json
import os
import re
from pathlib import Path

RULES_PATH = Path(__file__).parent / "rules.json"
DEFAULT_MODEL = os.environ.get("LEASECHECK_MODEL", "claude-sonnet-5-5")
SEVERITY_ORDER = {"red": 0, "yellow": 1, "green": 2}


def load_rules():
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Get plain text from an uploaded .pdf or .txt lease."""
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return file_bytes.decode("utf-8", errors="ignore")


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9$%]+", " ", s.lower()).strip()


def quote_is_in_lease(quote: str, lease_text: str) -> bool:
    """Guard against made-up quotes: the quoted clause must actually appear in the lease."""
    q = _normalize(quote)
    return len(q) > 0 and q in _normalize(lease_text)


# ---------------------------------------------------------------- AI mode

PROMPT = """You are LeaseCheck, a tool that helps college students spot risky clauses in a residential lease in Philadelphia, Pennsylvania.
You do NOT give legal advice. You only flag clauses that match the rules below and explain them in plain English.

RULES (only flag clauses that match one of these):
{rules}

LEASE:
<lease>
{lease}
</lease>

Instructions:
- For every clause that matches a rule, return one finding.
- "quote" must be copied EXACTLY from the lease (one sentence or short clause, under 60 words).
- "explanation" is 1-2 plain-English sentences a first-time renter would understand, specific to this lease (mention the actual numbers if there are any).
- Only flag a rule if the lease text clearly supports it. If unsure, leave it out.
- Return ONLY JSON in this format, with no other text:
{{"findings": [{{"rule_id": "R01", "quote": "...", "explanation": "..."}}]}}
"""


def ai_check(lease_text: str, rules: list, api_key: str, model: str = DEFAULT_MODEL) -> list:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    rules_text = "\n".join(
        f"- {r['id']} ({r['severity']}) {r['name']}: {r['what_to_look_for']}" for r in rules
    )
    msg = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": PROMPT.format(rules=rules_text, lease=lease_text)}],
    )
    raw = "".join(block.text for block in msg.content if block.type == "text")
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    data = json.loads(match.group(0)) if match else {"findings": []}
    return data.get("findings", [])


# ---------------------------------------------------------------- Demo mode

# Keyword patterns per rule. Rough on purpose: this is only so the app runs without an API key.
DEMO_PATTERNS = {
    "R01": [r"(three|3|four|4)\s*\(?\d?\)?\s*months?'? rent", r"deposit[^.]{0,80}(three|3|four|4) months"],
    "R02": [r"(45|60|90|forty-five|sixty|ninety)\s*(\(\d+\)\s*)?days[^.]{0,80}(deposit|vacat|move)", r"(deposit|vacat)[^.]{0,120}(45|60|90|forty-five|sixty|ninety)\s*(\(\d+\)\s*)?days"],
    "R03": [r"non-?refundable"],
    "R04": [r"tenant[^.]{0,60}(responsible|pay)[^.]{0,40}all repairs", r"all repairs[^.]{0,80}(heat|plumbing|electrical|roof|structur)"],
    "R05": [r"landlord (shall|will) not be (liable|responsible) for any"],
    "R06": [r"enter[^.]{0,60}(at any time|without (prior )?notice)"],
    "R07": [r"confess(es|ion of)? judgment", r"waives?[^.]{0,40}(notice to quit|right to (a )?(notice|trial|hearing))"],
    "R08": [r"late fee[^.]{0,80}(per day|each day|daily)", r"(per day|each day|daily)[^.]{0,60}late"],
    "R09": [r"automatically renew"],
    "R10": [r"(increase|raise|adjust) (the )?rent[^.]{0,60}(at any time|during the (lease )?term)"],
    "R11": [r"tenant[^.]{0,60}(pay|reimburse)[^.]{0,60}(attorney|legal)['s]* fees"],
    "R12": [r"jointly and severally"],
}


def demo_check(lease_text: str, rules: list) -> list:
    sentences = re.split(r"(?<=[.;])\s+", lease_text.replace("\n", " "))
    findings = []
    for rule in rules:
        for pattern in DEMO_PATTERNS.get(rule["id"], []):
            hit = next((s for s in sentences if re.search(pattern, s, re.IGNORECASE)), None)
            if hit:
                findings.append({
                    "rule_id": rule["id"],
                    "quote": hit.strip(),
                    "explanation": rule["why_it_matters"],
                })
                break
    return findings


# ---------------------------------------------------------------- Main entry point

def check_lease(lease_text: str, api_key: str | None = None, model: str = DEFAULT_MODEL) -> dict:
    """Returns {"mode": "ai"|"demo", "findings": [...], "dropped": n} with rule info merged in."""
    rules = load_rules()
    by_id = {r["id"]: r for r in rules}

    if api_key:
        raw, mode = ai_check(lease_text, rules, api_key, model), "ai"
    else:
        raw, mode = demo_check(lease_text, rules), "demo"

    findings, dropped = [], 0
    for f in raw:
        rule = by_id.get(f.get("rule_id"))
        if not rule or not quote_is_in_lease(f.get("quote", ""), lease_text):
            dropped += 1  # unknown rule or a quote that isn't really in the lease
            continue
        findings.append({**rule, "quote": f["quote"], "explanation": f.get("explanation") or rule["why_it_matters"]})

    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])
    return {"mode": mode, "findings": findings, "dropped": dropped}
