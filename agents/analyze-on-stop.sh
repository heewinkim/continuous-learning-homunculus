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

total_lines=$(wc -l < "$OBSERVATIONS_FILE" 2>/dev/null | tr -d ' ' || echo 0)

# Track last analyzed line number (not timestamp)
LAST_LINE=0
if [ -f "$LAST_ANALYZED_FILE" ]; then
  LAST_LINE=$(cat "$LAST_ANALYZED_FILE" 2>/dev/null | tr -d ' ' || echo 0)
  # Reset if file was re-created (line count went backwards)
  if [ "$LAST_LINE" -gt "$total_lines" ]; then
    LAST_LINE=0
  fi
fi

new_lines=$((total_lines - LAST_LINE))
if [ "$new_lines" -lt "$MIN_OBSERVATIONS" ]; then
  echo "[$(date)] Skipped: only $new_lines new observations (min: $MIN_OBSERVATIONS)" >> "$LOG_FILE"
  exit 0
fi

echo "[$(date)] Session ended. Analyzing $new_lines new observations (lines $((LAST_LINE+1))-$total_lines)..." >> "$LOG_FILE"

# Run Claude Haiku analysis
if ! command -v claude &> /dev/null; then
  echo "[$(date)] claude CLI not found" >> "$LOG_FILE"
  exit 1
fi

# Read only NEW observations since last analysis
OBS_CONTENT=$(tail -n +"$((LAST_LINE + 1))" "$OBSERVATIONS_FILE" | head -c 40000 2>/dev/null)
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

PROMPT="You are an instinct extractor. Analyze the observations below and output instinct file blocks.

OBSERVATIONS (JSON lines from a Claude Code session):
---
$OBS_CONTENT
---

EXISTING INSTINCTS (already learned — check before creating):
---
$EXISTING_INSTINCTS
---

$CAPACITY_NOTE

## Philosophy
A small set of deep, accurate instincts beats many shallow ones.
When in doubt, output nothing.

## What to look for (human character, not tool mechanics)
- Moments the user pushed back, corrected, or said no — what value was defended?
- What they consistently accept vs. reject
- How they prefer to communicate — tone, directness, depth
- What they consistently avoid or dislike
- How they approach hard problems

## Rules
1. Minimum confidence 0.65. Skip weak or one-off signals.
2. If a signal reinforces an existing instinct, output an updated version of that file.
3. Only output a new file if the pattern is clearly not covered by existing instincts.
4. No tool-use noise ('used Bash a lot' is not an instinct).
5. If nothing qualifies, output exactly: NO_INSTINCTS

## Output format
For each instinct (new or updated), output a block like this — nothing else:

<<<FILE:kebab-case-id.md>>>
---
id: kebab-case-id
trigger: \"one specific situation\"
confidence: 0.65-0.9
domain: \"values|aesthetics|philosophy|communication|habits|curiosity|rhythm|expression\"
source: \"session-observation\"
---

# 제목 (한국어)

## Insight
한 문장 — 이 사람이 어떤 사람인지 (무엇을 해야 하는지 X)

## In Practice
한두 문장 — 이 인사이트를 어떻게 적용하는지

## Evidence
- $TODAY 기준 N회 관찰
<<<END>>>

Output ONLY the <<<FILE>>>...<<<END>>> blocks or NO_INSTINCTS. No explanation, no commentary."

# Run analysis and capture output
unset CLAUDECODE
ANALYSIS_OUTPUT=$(claude --model haiku --max-turns 3 --print "$PROMPT" 2>&1)
exit_code=$?

echo "[$(date)] Claude output captured (${#ANALYSIS_OUTPUT} chars)" >> "$LOG_FILE"

if [ "$exit_code" -ne 0 ]; then
  echo "[$(date)] Analysis failed (exit $exit_code): $ANALYSIS_OUTPUT" >> "$LOG_FILE"
  exit 0
fi

# Check if no instincts found
if echo "$ANALYSIS_OUTPUT" | grep -q "^NO_INSTINCTS"; then
  echo "[$(date)] No qualifying instincts found." >> "$LOG_FILE"
  echo "$total_lines" > "$LAST_ANALYZED_FILE"
  exit 0
fi

# Parse output and write instinct files
FILES_WRITTEN=$(echo "$ANALYSIS_OUTPUT" | python3 -c "
import sys, os, re

output = sys.stdin.read()
instincts_dir = '$INSTINCTS_DIR'
os.makedirs(instincts_dir, exist_ok=True)

pattern = r'<<<FILE:(.+?)>>>(.*?)<<<END>>>'
matches = re.findall(pattern, output, re.DOTALL)

count = 0
for filename, content in matches:
    filename = filename.strip()
    content = content.strip()
    if not filename.endswith('.md'):
        filename += '.md'
    filepath = os.path.join(instincts_dir, filename)
    with open(filepath, 'w') as f:
        f.write(content + '\n')
    print(f'Written: {filename}')
    count += 1

if count == 0:
    print('No FILE blocks found in output')
    sys.exit(1)
" 2>&1)

parse_exit=$?
echo "[$(date)] $FILES_WRITTEN" >> "$LOG_FILE"

if [ $parse_exit -eq 0 ]; then
  echo "[$(date)] Analysis complete. Marked line $total_lines as analyzed." >> "$LOG_FILE"
  echo "$total_lines" > "$LAST_ANALYZED_FILE"
else
  echo "[$(date)] Parse failed. Raw output: ${ANALYSIS_OUTPUT:0:500}" >> "$LOG_FILE"
fi

exit 0
