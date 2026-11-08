"""Dialect identification: vocabulary matching first, LLM as fallback."""
import json
import re
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VOCAB_DIR = BASE_DIR / "vocabulary"

ALLOWED_DIALECTS = ["Dinajpur", "Rangpur", "Standard Bangla", "Other/Uncertain"]
# If Rangpur and Dinajpur evidence is equal, choose this dialect.
OVERLAP_FALLBACK_DIALECT = "Rangpur"

BANGLA_RE = re.compile(r"[\u0980-\u09FF]")


# ---------------------------------------------------------------- text utils
def normalize_word(word):
    return re.sub(r"[^\u0980-\u09FF]", "", str(word).strip().lower())


def tokenize(text):
    tokens = re.findall(r"[\u0980-\u09FF\u200c\u200d]+", str(text).lower())
    return [t.replace("\u200c", "").replace("\u200d", "") for t in tokens]


def has_bangla(text):
    return bool(BANGLA_RE.search(str(text)))


# ------------------------------------------------------------- vocabularies
def load_vocabulary(filename):
    path = VOCAB_DIR / filename
    if not path.exists():
        print(f"Warning: {filename} not found!")
        return set()
    content = path.read_text(encoding="utf-8")
    content = "\n".join(l for l in content.splitlines() if not l.strip().startswith("#"))
    words = re.split(r"[,\u060c\n]+", content)
    return {normalize_word(w) for w in words if normalize_word(w)}


SHARED_WORDS = load_vocabulary("north_bengal_shared.txt")
RANGPUR_WORDS = load_vocabulary("rangpur.txt")
DINAJPUR_WORDS = load_vocabulary("dinajpur.txt")


# ------------------------------------------------- vocabulary-based detection
def vocabulary_detection(text):
    token_counts = Counter(tokenize(text))

    rangpur_matches = {w for w in token_counts if w in RANGPUR_WORDS}
    dinajpur_matches = {w for w in token_counts if w in DINAJPUR_WORDS}
    shared_matches = {w for w in token_counts if w in SHARED_WORDS}
    overlap_matches = rangpur_matches & dinajpur_matches
    rangpur_excl = rangpur_matches - DINAJPUR_WORDS
    dinajpur_excl = dinajpur_matches - RANGPUR_WORDS

    def count(words):
        return sum(token_counts[w] for w in words)

    rangpur_score, dinajpur_score = count(rangpur_excl), count(dinajpur_excl)
    overlap_score, shared_score = count(overlap_matches), count(shared_matches)

    base = {
        "rangpur_score": rangpur_score,
        "dinajpur_score": dinajpur_score,
        "overlap_score": overlap_score,
        "shared_score": shared_score,
        "rangpur_matches": sorted(rangpur_matches),
        "dinajpur_matches": sorted(dinajpur_matches),
        "overlap_matches": sorted(overlap_matches),
        "shared_matches": sorted(shared_matches),
    }

    if not rangpur_matches and not dinajpur_matches:
        return {"detected": False, **base}

    if rangpur_score > dinajpur_score:
        dialect, win, lose, clues = "Rangpur", rangpur_score, dinajpur_score, sorted(rangpur_excl)
    elif dinajpur_score > rangpur_score:
        dialect, win, lose, clues = "Dinajpur", dinajpur_score, rangpur_score, sorted(dinajpur_excl)
    elif overlap_score > 0 or (rangpur_score > 0 and dinajpur_score > 0):
        dialect = OVERLAP_FALLBACK_DIALECT
        win = lose = max(rangpur_score, dinajpur_score)
        clues = sorted(overlap_matches)
    else:
        return {"detected": False, **base}

    if win == lose:
        confidence = 0.68
    else:
        confidence = min(0.95, 0.72 + ((win - lose) / max(win + lose, 1)) * 0.20)

    return {"detected": True, "dialect": dialect, "confidence": round(confidence, 2),
            "linguistic_clues": clues, **base}


# ------------------------------------------------------------ LLM fallback
def extract_json(content):
    if isinstance(content, list):
        content = "".join(i.get("text", "") if isinstance(i, dict) else str(i)
                          for i in content)
    content = str(content).strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Invalid JSON response.")
    return json.loads(content[start:end + 1])


def llm_dialect_detection(text, evidence):
    from langchain_core.messages import SystemMessage, HumanMessage
    from dialect.llm import get_llm

    system_prompt = f"""
You are an expert Bangla regional linguist.
Identify the likely dialect of the given text.
Available labels: Dinajpur, Rangpur, Standard Bangla, Other/Uncertain

INSTRUCTIONS:
- Analyze regional vocabulary, grammar, pronouns, verb conjugations,
  spelling variations and Bangla-English code mixing.
- Analyze the entire sentence, not just one word.
- Dinajpur and Rangpur dialects can overlap; do not assume every North Bengal
  word is exclusive to one district.
- If there is reasonable evidence for either regional dialect, choose the more
  likely one. If both are equally likely, choose Rangpur.
- Do not automatically classify a short sentence as Standard Bangla.
- Do not invent linguistic clues.
- Use Other/Uncertain only when there is insufficient linguistic evidence.

VOCABULARY EVIDENCE:
{json.dumps(evidence, ensure_ascii=False)}

Shared vocabulary cannot independently prove a particular district.

Return ONLY valid JSON:
{{
 "dialect": "Dinajpur",
 "confidence": 0.80,
 "explanation": "বাংলায় ব্যাখ্যা",
 "linguistic_clues": ["আঞ্চলিক শব্দ"],
 "alternative": "Rangpur"
}}
Confidence is an uncalibrated model estimate.
"""
    response = get_llm().invoke([SystemMessage(content=system_prompt),
                                 HumanMessage(content=text)])
    return extract_json(response.content)


# ------------------------------------------------------------- main function
def _result(dialect, confidence, explanation, clues, alternative, method, evidence=None):
    out = {"dialect": dialect, "confidence": confidence, "explanation": explanation,
           "linguistic_clues": clues, "alternative": alternative, "method": method}
    if evidence is not None:
        out["vocabulary_evidence"] = evidence
    return out


def identify_dialect(text):
    if not text or not str(text).strip():
        return _result("Other/Uncertain", 0.0, "কোনো টেক্সট প্রদান করা হয়নি।",
                       [], None, "No Input")
    text = str(text).strip()

    if not has_bangla(text):
        return _result("Other/Uncertain", 0.0,
                       "লেখাটিতে বাংলা অক্ষর নেই, তাই আঞ্চলিক ভাষা শনাক্ত করা যায়নি। "
                       "বাংলা হরফে লিখে আবার চেষ্টা করো।",
                       [], None, "No Bangla Script")

    evidence = vocabulary_detection(text)

    if evidence["detected"]:
        dialect = evidence["dialect"]
        if evidence["overlap_matches"]:
            explanation = ("Dinajpur এবং Rangpur dialect-এর কিছু overlapping আঞ্চলিক শব্দ পাওয়া গেছে। "
                           f"নির্ধারিত tie-breaking নিয়ম অনুযায়ী {dialect} নির্বাচন করা হয়েছে।")
        else:
            explanation = f"আঞ্চলিক vocabulary matching-এর মাধ্যমে {dialect} dialect শনাক্ত করা হয়েছে।"
        return _result(dialect, evidence["confidence"], explanation,
                       evidence["linguistic_clues"],
                       "Dinajpur" if dialect == "Rangpur" else "Rangpur",
                       "Hybrid-Vocabulary", evidence)

    try:
        result = llm_dialect_detection(text, evidence)
    except Exception as error:
        print("Dialect LLM Error:", error)
        return _result("Other/Uncertain", 0.0,
                       "ভাষাগত বৈশিষ্ট্য থেকে নিশ্চিত সিদ্ধান্ত পাওয়া যায়নি।",
                       [], None, "Fallback", evidence)

    dialect = result.get("dialect")
    if dialect not in ALLOWED_DIALECTS:
        dialect = "Other/Uncertain"
    try:
        confidence = max(0.0, min(1.0, float(result.get("confidence", 0))))
    except (ValueError, TypeError):
        confidence = 0.0
    clues = result.get("linguistic_clues", [])
    if not isinstance(clues, list):
        clues = []
    alternative = result.get("alternative")
    if alternative not in ALLOWED_DIALECTS:
        alternative = None
    return _result(dialect, round(confidence, 2),
                   result.get("explanation", "ভাষাগত বৈশিষ্ট্য বিশ্লেষণ করা হয়েছে।"),
                   [str(c) for c in clues], alternative, "LLM-Based", evidence)
