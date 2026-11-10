# History myth reels for @did.you.know9104

Fully automatic Instagram Reels that take one popular history "fact" and reveal the truth:
**Myth or fact? → 3-second countdown → MYTH/FACT stamp → narrated reality → where the myth came from → sources.**

Everything runs on free GitHub Actions. The only paid piece is the Claude subscription (via `claude -p`).

## How it works

| Workflow | When | What |
|---|---|---|
| `post.yml` | `41 2,6,10,14 * * *` (~08:11, 12:11, 16:11, 20:11 IST) + manual | Reconcile, find due slots (catch-up first), pick a myth, voice, render, validate, publish, commit state |
| `refill.yml` | Sunday ~02:35 IST + manual | Research new myths until the backlog reaches 40 (time-boxed), then keep schedules alive |
| `checks.yml` | manual | Secret scan + tests |

**Posting ramp** (automatic, from `start_date` in `config.yaml`):
- Days 1-14: 1 reel/day (slot 4).
- Days 15-30: 2/day (slots 2, 4).
- Day 31 onwards: 3/day (slots 1, 2, 4).

There's a hard cap of 3/day. A run with no due slot exits in seconds.

**Content pipeline** (accuracy first). Every myth goes through:
1. `claude -p` writes candidates as strict JSON (schema-validated).
2. Research pass (web search + fetch): every beat and the verdict need ≥2 independent reliable sources. Wikipedia, forums and listicles don't count.
3. Local checks: source count per beat, excluded topics, nothing from the last 30 years, fuzzy dedup against history and backlog.
4. Adversarial pass: a skeptical historian searches for counter-evidence. Any genuine dispute or exclusion means rejection.

Approved myths wait in `state/myths_backlog.json` (human-readable, so you *can* delete entries before they post, but nothing requires it).

**Each reel:**
- Format: 1080x1920, 30 fps, H.264/AAC, 30-75 s.
- Voiceover is mandatory: edge-tts first, Piper offline fallback, never mixed within a reel. If both fail, the slot is skipped.
- Audio: Python builds one pre-mixed master track (narration, synthesized tick/thud/whoosh, optional ducked music), normalized to -14 LUFS.
- Video: Remotion renders the visuals at the exact frames Python's timeline gives. Images are public-domain/CC0 only, from Wikimedia Commons; when none are found it falls back to an animated timeline motif.
- Validation (ffprobe + silencedetect): duration, resolution, fps, AAC track, A/V length, real speech, subtitles, caption, sources, verdict. Anything failing is never published. The slot is skipped and a GitHub Issue opens (one per failure type per 24 h).

## Commands

```bash
python -m mythreels dry-run --claim "Vikings wore horned helmets"   # research + render locally, no posting
python -m mythreels dry-run                                          # next backlog myth
python -m mythreels refill --budget-minutes 30                       # research myths into the backlog
python -m mythreels due                                              # which slots are due now
python -m mythreels post --mode publish-test                         # one real reel (needs IG secrets in env)
python -m mythreels voices                                           # sample several edge-tts narrators
python -m mythreels ig-check                                         # verify IG_ACCESS_TOKEN / IG_USER_ID
python -m pytest -q                                                  # tests
cd remotion && npm run studio                                        # preview the composition in Remotion Studio
```

Dry-run output lands in `output/dry-run/<myth-id>/`: the MP4, `research_log.json` (sources per beat + reviews), `caption.txt`, `report.json`.

## Local setup

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # (.venv/bin/pip on Mac/Linux)
cd remotion && npm ci && npx remotion browser ensure && cd ..
git config core.hooksPath .githooks                                      # pre-commit secret scan
```

Needs Python 3.12, Node 22+, ffmpeg and the Claude Code CLI (`claude`) on PATH.

## Files

- `config.yaml`: schedule, ramp, categories, exclusions, voice, audio levels, palette.
- `state/myths_backlog.json`: approved, researched myths waiting to be posted.
- `state/published_history.json`: every slot outcome (`pending` / `published` / `failed`). Used for catch-up, dedup, the 30-day person cooldown and crash reconciliation.
- `mythreels/`: Python package (one module per concern).
- `remotion/`: the `MythReel` composition.
- `assets/music/`: drop royalty-free tracks here (optional). They're mixed at about -25 dB and ducked under speech.

## Remotion license

Remotion is free for individuals and for-profit organisations with up to 3 employees. Larger companies need a
company license. See <https://www.remotion.dev/license>. This account is run by an individual.
