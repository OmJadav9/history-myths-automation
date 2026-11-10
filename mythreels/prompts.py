import json

HARD_EXCLUSIONS = """HARD EXCLUSIONS (never use): religion and religious figures; caste; communal or religious-conflict
narratives; partisan or current politics; ongoing territorial disputes; living people; events from the last
30 years; wars, atrocities or genocide where a "myth" framing could minimise or deny harm; conspiracy
theories; anything historians actively dispute. NEVER present an established historical fact as a myth."""

RELIABLE = """Reliable sources: encyclopaedias (e.g. Britannica), museums, universities, national archives,
academic publishers and journals, reputable history outlets (e.g. Smithsonian Magazine, History Extra, BBC
History, National Geographic History). Wikipedia does NOT count as a source (use it only to find sources).
Never cite forums, social media, Q&A sites, listicle/content-farm sites or AI-generated pages."""


def generate(n: int, categories: list[str], preferred: list[str], fact_pct: int, avoid: list[str],
             seed_claim: str | None) -> str:
    seed = f'\nCandidate 1 MUST be about exactly this claim: "{seed_claim}".' if seed_claim else ""
    return f"""You write candidate scripts for @did.you.know9104, an Instagram account of 30-75 second narrated
reels. Each reel takes ONE popular history "fact" and reveals the truth: "Myth or fact?" -> the viewer guesses
-> a stamp reveals MYTH or FACT -> a narrated explanation -> where the myth came from.

Write {n} candidates. About {fact_pct}% should be FACT (a claim that sounds fake but is true); the rest MYTH.
Use these exact category strings: {json.dumps(categories)}. Favour these under-used ones: {json.dumps(preferred)}.
Spread candidates across categories.{seed}

Do NOT repeat or closely paraphrase any of these existing claims:
{json.dumps(avoid, ensure_ascii=False)}

{HARD_EXCLUSIONS}

Only pick myths where mainstream historians clearly agree on the truth, so it can be backed by at least two
independent reliable sources.

Field rules:
- claim: the belief exactly as people say it, max 90 characters, e.g. "Vikings wore horned helmets."
- hook: a curiosity line for the caption, max 70 characters.
- reality: 3-5 beats ordered STRONGEST FIRST. narration = 1-2 short spoken sentences (max ~30 words) with
  concrete dates, numbers or names. key_line = a bold on-screen line, max 40 characters.
- origin: 1-2 beats on where the myth came from (for a FACT: why it sounds false).
- summary: 2-3 plain sentences for the caption.
- year: one representative year (negative for BC). era: e.g. "Viking Age".
- key_people: main person first ([] if none). event: a short name for the topic. key_places: places involved.
- image_search_terms: 3-4 Wikimedia Commons searches. Only public-domain files are used, so aim at OLD artwork:
  include words like "painting", "engraving", "illustration", "manuscript", "map" or "portrait" plus a name or
  place (e.g. "Viking warriors painting", "Napoleon portrait", "Mughal miniature painting"). Never living
  people, nothing graphic or violent.
- hashtags: 8-10 like "#history".
- pronunciations: tricky names or words with an easy phonetic spelling for text-to-speech,
  e.g. {{"word": "Gjermundbu", "say": "Yer-mund-boo"}}. [] if none.

Write for the ear: short sentences, no parentheses, no abbreviations except BC and AD, no URLs. Don't write a
verdict line, intro or outro: those are added automatically. Aim for 110-150 words of narration in total
(reality + origin), so the reel lands at 45-65 seconds. Use hedged wording ("historians believe", "the earliest
record is") wherever the evidence calls for it."""


def research(candidate: dict) -> str:
    return f"""You are the fact-checker for a history myth-busting Instagram account. Accuracy is the top priority:
a wrong "reality" spreads a new myth.

Candidate script (JSON):
{json.dumps(candidate, ensure_ascii=False, indent=1)}

Use WebSearch and WebFetch to verify the verdict and EVERY factual sentence in the reality and origin narrations.
{RELIABLE}

Rules:
- Every beat needs at least 2 sources from 2 different organisations that support every factual sentence in it.
  Open each page you cite and record its exact title, URL and publisher.
- verdict_sources: at least 2 sources from different organisations that directly support the MYTH/FACT verdict.
- Dates, numbers and names must match the sources exactly. Rewrite narration and key_line to match what the
  sources say, and hedge wherever they do. Keep narration short and written for the ear.
- Drop or rewrite any beat you cannot support. Keep 3-5 reality beats (strongest first) and 1-2 origin beats.
- Keep every other field, correcting it if inaccurate.
- If the verdict is wrong or disputed, or you cannot source it properly, set keep=false and explain why.

{HARD_EXCLUSIONS}"""


def adversarial(myth: dict) -> str:
    return f"""You are a skeptical professional historian. A myth-busting reel is about to be published to a large
audience. Your job is to find reasons NOT to publish it.

Script with its sources (JSON):
{json.dumps(myth, ensure_ascii=False, indent=1)}

1. Actively search (WebSearch/WebFetch) for counter-evidence, scholarly disagreement or newer research that
   contradicts the verdict or any beat. Is the "myth" actually an established fact? Is the "fact" disputed?
2. Open several cited pages and check they are real, reliable, and actually say what the script claims.
3. Check that dates, numbers and names are exact, and that uncertain points are hedged.
4. Check the HARD EXCLUSIONS below; set exclusion_hit=true if any apply.

Answer with:
- genuine_dispute=true only if historians genuinely disagree about the verdict, or the verdict is wrong.
- exclusion_hit=true if any hard exclusion applies.
- fixes_needed: every concrete change that must be made before publishing (overstated or unsupported claims,
  misrepresented or unreliable sources, wrong or loosely rounded numbers/dates/names, missing hedges, a hook
  that contradicts the body). Be specific: quote the text and say what it should become. [] if publishable.
- reason: your overall assessment.

{HARD_EXCLUSIONS}
{RELIABLE}"""


def revise(myth: dict, fixes: list[str]) -> str:
    return f"""You are the fact-checker for a history myth-busting Instagram account. A skeptical historian reviewed
this script and requires the fixes below before it can be published.

Script with its sources (JSON):
{json.dumps(myth, ensure_ascii=False, indent=1)}

Required fixes:
{json.dumps(fixes, ensure_ascii=False, indent=1)}

Apply EVERY fix. Use WebSearch/WebFetch wherever a fix needs new or better sources. All the original rules
still apply: every beat and the verdict need at least 2 sources from 2 different organisations that you have
opened; dates, numbers and names must match the sources exactly; hedge wherever the evidence does; 3-5 reality
beats (strongest first) and 1-2 origin beats; short sentences written for the ear; the hook and summary must
agree with the body. If the fixes can't be made while keeping a sound, sourced script, set keep=false.

{RELIABLE}
{HARD_EXCLUSIONS}"""
