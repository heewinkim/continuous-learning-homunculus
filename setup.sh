#!/bin/bash
# continuous-learning-homunculus setup script
set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="${HOME}/.claude/settings.json"
HOMUNCULUS_DIR="${HOME}/.claude/homunculus"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo "continuous-learning-homunculus setup"
echo "────────────────────────────"
echo ""

# ── Prerequisites ──────────────────────────────────────────────────────────

command -v python3 &>/dev/null || fail "python3가 필요합니다"
ok "python3 found"

command -v claude &>/dev/null || warn "claude CLI를 찾을 수 없습니다. 설치 후 분석 기능이 활성화됩니다."

# ── Make scripts executable ────────────────────────────────────────────────

chmod +x "$SKILL_DIR/hooks/observe.sh"
chmod +x "$SKILL_DIR/agents/analyze-on-stop.sh"
chmod +x "$SKILL_DIR/agents/start-observer.sh"
ok "스크립트 실행 권한 설정 완료"

# ── Create continuous-learning-homunculus directory structure ──────────────────────────────────

mkdir -p \
  "$HOMUNCULUS_DIR/instincts/personal" \
  "$HOMUNCULUS_DIR/instincts/inherited" \
  "$HOMUNCULUS_DIR/evolved/skills" \
  "$HOMUNCULUS_DIR/evolved/commands" \
  "$HOMUNCULUS_DIR/evolved/agents" \
  "$HOMUNCULUS_DIR/observations.archive"

touch "$HOMUNCULUS_DIR/observations.jsonl"
ok "~/.claude/homunculus 디렉토리 구조 생성 완료"

# ── Patch settings.json ────────────────────────────────────────────────────

if [ ! -f "$SETTINGS_FILE" ]; then
  echo '{}' > "$SETTINGS_FILE"
  warn "settings.json이 없어서 새로 생성했습니다"
fi

python3 - "$SETTINGS_FILE" "$SKILL_DIR" <<'PYEOF'
import json
import sys
import os

settings_path = sys.argv[1]
skill_dir = sys.argv[2]

with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})

OBSERVE_PRE  = f"{skill_dir}/hooks/observe.sh pre"
OBSERVE_POST = f"{skill_dir}/hooks/observe.sh post"
ANALYZE_STOP = f"{skill_dir}/agents/analyze-on-stop.sh"

def normalize(cmd):
    """Expand ~ so tilde and absolute paths match."""
    return os.path.expanduser(cmd)

def hook_exists(hook_list, command):
    target = normalize(command.split()[0])
    for entry in hook_list:
        for h in entry.get("hooks", []):
            existing = normalize(h.get("command", "").split()[0])
            if existing == target:
                return True
    return False

# PreToolUse — observe pre
pre_hooks = hooks.setdefault("PreToolUse", [])
if not hook_exists(pre_hooks, OBSERVE_PRE):
    pre_hooks.append({
        "matcher": "*",
        "hooks": [{"type": "command", "command": OBSERVE_PRE}]
    })

# PostToolUse — observe post
post_hooks = hooks.setdefault("PostToolUse", [])
if not hook_exists(post_hooks, OBSERVE_POST):
    post_hooks.append({
        "matcher": "*",
        "hooks": [{"type": "command", "command": OBSERVE_POST}]
    })

# Stop — analyze on session end
stop_hooks = hooks.setdefault("Stop", [])
if not hook_exists(stop_hooks, ANALYZE_STOP):
    stop_hooks.append({
        "matcher": "*",
        "hooks": [{"type": "command", "command": ANALYZE_STOP, "async": True}]
    })

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("ok")
PYEOF

ok "~/.claude/settings.json 훅 등록 완료 (PreToolUse, PostToolUse, Stop)"

# ── Register slash commands ─────────────────────────────────────────────────

COMMANDS_DIR="${HOME}/.claude/commands"
mkdir -p "$COMMANDS_DIR"

EVOLVE_SRC="$SKILL_DIR/commands/evolve.md"
EVOLVE_DST="$COMMANDS_DIR/evolve.md"

if [ -f "$EVOLVE_SRC" ]; then
  cp "$EVOLVE_SRC" "$EVOLVE_DST"
  ok "/evolve 슬래시 커맨드 등록 완료 (~/.claude/commands/evolve.md)"
else
  warn "/evolve 커맨드 소스를 찾을 수 없습니다: $EVOLVE_SRC"
fi

# ── Done ───────────────────────────────────────────────────────────────────

echo ""
echo "────────────────────────────"
echo -e "${GREEN}설치 완료!${NC}"
echo ""
echo "  동작 방식:"
echo "  • 세션 중: 모든 툴 호출이 자동으로 기록됩니다"
echo "  • 세션 종료 시: Claude Haiku가 패턴을 분석하고 instinct를 생성합니다"
echo "  • instinct 생성 후: 자동으로 evolve 실행 → skills/commands/agents 생성"
echo ""
echo "  슬래시 커맨드:"
echo "  /evolve          — 수동으로 즉시 evolve 실행"
echo ""
echo "  CLI 사용법:"
echo "  python3 $SKILL_DIR/scripts/instinct-cli.py status"
echo "  python3 $SKILL_DIR/scripts/instinct-cli.py evolve --generate"
echo "  python3 $SKILL_DIR/scripts/instinct-cli.py export -o my-profile.yaml"
echo ""
echo "  데이터 위치: ~/.claude/homunculus/"
echo ""
