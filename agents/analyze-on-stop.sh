#!/bin/bash
# Continuous Learning v2 - Session-End Analysis
#
# Triggered by the Stop hook when a Claude Code session ends.
# Analyzes accumulated observations and creates/updates instincts.
# Runs once per session — no background daemon needed.

CONFIG_DIR="${HOME}/.claude/homunculus"
OBSERVATIONS_FILE="${CONFIG_DIR}/observations.jsonl"
INSTINCTS_DIR="${CONFIG_DIR}/instincts/personal"
LOG_FILE="${CONFIG_DIR}/observer.log"
LAST_ANALYZED_FILE="${CONFIG_DIR}/.last_analyzed"

MIN_OBSERVATIONS=20

mkdir -p "$CONFIG_DIR" "$INSTINCTS_DIR"

# Skip if disabled
if [ -f "$CONFIG_DIR/disabled" ]; then
  exit 0
fi

# Check observation count
if [ ! -f "$OBSERVATIONS_FILE" ]; then
  exit 0
fi

obs_count=$(wc -l < "$OBSERVATIONS_FILE" 2>/dev/null | tr -d ' ' || echo 0)
if [ "$obs_count" -lt "$MIN_OBSERVATIONS" ]; then
  echo "[$(date)] Skipped: only $obs_count observations (min: $MIN_OBSERVATIONS)" >> "$LOG_FILE"
  exit 0
fi

# Check if there are new observations since last analysis
if [ -f "$LAST_ANALYZED_FILE" ]; then
  last_analyzed=$(cat "$LAST_ANALYZED_FILE")
  obs_modified=$(stat -f "%m" "$OBSERVATIONS_FILE" 2>/dev/null || stat -c "%Y" "$OBSERVATIONS_FILE" 2>/dev/null || echo 0)
  if [ "$obs_modified" -le "$last_analyzed" ]; then
    echo "[$(date)] Skipped: no new observations since last analysis" >> "$LOG_FILE"
    exit 0
  fi
fi

echo "[$(date)] Session ended. Analyzing $obs_count observations..." >> "$LOG_FILE"

# Run Claude Haiku analysis
if ! command -v claude &> /dev/null; then
  echo "[$(date)] claude CLI not found" >> "$LOG_FILE"
  exit 1
fi

# Read observations content directly (avoid needing Read tool permission)
OBS_CONTENT=$(head -c 40000 "$OBSERVATIONS_FILE" 2>/dev/null)
TODAY=$(date +%Y-%m-%d)

# Build existing instincts summary with full content for merging decisions
EXISTING_INSTINCTS=""
INSTINCT_COUNT=0
MAX_INSTINCTS=15
if [ -d "$INSTINCTS_DIR" ]; then
  for f in "$INSTINCTS_DIR"/*.md; do
    [ -f "$f" ] || continue
    INSTINCT_COUNT=$((INSTINCT_COUNT + 1))
    fname=$(basename "$f" .md)
    summary=$(head -10 "$f" | grep -E "^(id|confidence|trigger):" | tr '\n' ' ')
    EXISTING_INSTINCTS="${EXISTING_INSTINCTS}- $fname: $summary\n"
  done
fi

if [ -z "$EXISTING_INSTINCTS" ]; then
  EXISTING_INSTINCTS="(none yet)"
fi

# Capacity state for prompt
if [ "$INSTINCT_COUNT" -ge "$MAX_INSTINCTS" ]; then
  CAPACITY_NOTE="CAPACITY REACHED ($INSTINCT_COUNT/$MAX_INSTINCTS). Do NOT create new files. You may only UPDATE existing files or use the Bash tool to delete redundant ones (rm $INSTINCTS_DIR/<id>.md) before merging."
else
  REMAINING=$((MAX_INSTINCTS - INSTINCT_COUNT))
  CAPACITY_NOTE="Capacity: $INSTINCT_COUNT/$MAX_INSTINCTS instincts used. At most $REMAINING new files allowed — use slots sparingly."
fi

PROMPT="AUTOMATED INSTINCT EXTRACTION TASK.
CRITICAL: Do NOT ask any questions. Do NOT ask for permission. Do NOT offer choices.
Immediately analyze and act. No conversation.

Here are the observations from a Claude Code session (JSON lines):

---OBSERVATIONS START---
$OBS_CONTENT
---OBSERVATIONS END---

---EXISTING INSTINCTS---
$EXISTING_INSTINCTS
---END EXISTING INSTINCTS---

$CAPACITY_NOTE

## Philosophy: Simple is Best
A small set of deep, accurate instincts is far more valuable than many shallow ones.
Resist the urge to create. Default to doing nothing unless the signal is unmistakably clear.

## What to look for (human character, not tool mechanics)
- Moments the user pushed back, corrected, or said no — what value was being defended?
- What they consistently accept vs. reject — aesthetic or philosophical standard
- How they communicate — tone, directness, depth they respond well to
- What they avoid or find annoying
- How they approach hard problems

## Strict rules
1. **Threshold: 0.65 minimum confidence.** One-off signals don't qualify. Skip if uncertain.
2. **Merge first.** If a new signal reinforces an existing instinct, UPDATE that file (raise confidence, add to evidence). Do not create a duplicate.
3. **Consolidate when possible.** If two existing instincts overlap significantly, DELETE the weaker one (Bash: rm) and fold it into the stronger one.
4. **Create only when genuinely novel** — a pattern clearly not covered by any existing instinct.
5. **No tool-use noise.** 'Used Bash frequently' is not an instinct. Focus on character.
6. **When in doubt, do nothing.** Silence is better than a weak instinct.

## File format (for new or updated files)
Write to $INSTINCTS_DIR/<kebab-case-id>.md:
---
id: <kebab-case-id>
trigger: \"<one specific situation>\"
confidence: <0.65-0.9>
domain: \"<values|aesthetics|philosophy|communication|habits|curiosity|rhythm|expression>\"
source: \"session-observation\"
---

# <Short, specific title>

## Insight
<One sentence — who they are, not what to do>

## In Practice
<One to two sentences — how to act on this>

## Evidence
- Observed <N> times across sessions
- Last observed: $TODAY

모든 파일 내용(Insight, In Practice, Evidence 포함)은 **한국어**로 작성할 것. id와 frontmatter 필드값(kebab-case id, domain 값 등)만 영어 유지.

BEGIN NOW. Less is more."

exit_code=0
unset CLAUDECODE
claude --model haiku --max-turns 15 --dangerously-skip-permissions --print "$PROMPT" >> "$LOG_FILE" 2>&1 || exit_code=$?

if [ "$exit_code" -eq 0 ]; then
  echo "[$(date)] Analysis complete." >> "$LOG_FILE"
  date +%s > "$LAST_ANALYZED_FILE"

  # Archive processed observations
  archive_dir="${CONFIG_DIR}/observations.archive"
  mkdir -p "$archive_dir"
  mv "$OBSERVATIONS_FILE" "$archive_dir/processed-$(date +%Y%m%d-%H%M%S).jsonl" 2>/dev/null || true
  touch "$OBSERVATIONS_FILE"
else
  echo "[$(date)] Analysis failed (exit $exit_code)" >> "$LOG_FILE"
fi

exit 0
