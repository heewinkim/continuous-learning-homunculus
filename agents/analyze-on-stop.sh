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

PROMPT="Read the observations file at $OBSERVATIONS_FILE. Your goal is NOT to catalog what tools were used — it is to understand the person behind the session: their values, philosophy, habits, and character.

Look for these human-centered patterns:

- value_corrections: moments the user said 'no', pushed back, or redirected — what principle or value was being asserted?
- aesthetic_standards: what does 'good' look like to this person? what did they accept vs. reject based on how something felt or looked?
- decision_philosophy: when faced with choices, what principles consistently guide them? (e.g. simplicity over completeness, speed over perfection)
- communication_preferences: how do they want to be spoken to? what tone, depth, and style do they respond well to?
- avoidance_patterns: what do they consistently not want? what makes them say 'no' or 'stop'?
- curiosity_areas: what topics or domains keep pulling their attention? what do they keep coming back to?
- work_rhythm: how do they naturally pace themselves? what does their working style look like?
- expression_style: how do they phrase things? what vocabulary, energy, or register do they use?
- priority_patterns: what do they consistently treat as most important when there is tension between options?
- problem_approach: when something is hard or broken, how do they characteristically respond?

For each clear pattern (2+ signals), create a file in $INSTINCTS_DIR/ named with a short kebab-case id.

File format:
---
id: <kebab-case-id>
trigger: \"<the situation where this applies>\"
confidence: <0.3-0.85>
domain: \"<one of: values, aesthetics, philosophy, communication, habits, curiosity, rhythm, expression>\"
source: \"session-observation\"
---

# <Title>

## Insight
<One sentence describing what this reveals about the person — not what to do, but who they are>

## In Practice
<How this should shape behavior when interacting with them>

## Evidence
- Observed <N> times
- Last observed: $(date +%Y-%m-%d)

Be honest and specific. Avoid generic observations. If a similar instinct already exists, deepen it rather than duplicate it."

exit_code=0
claude --model haiku --max-turns 15 --print "$PROMPT" >> "$LOG_FILE" 2>&1 || exit_code=$?

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
