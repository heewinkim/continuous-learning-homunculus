#!/bin/bash
# continuous-learning-homunculus uninstall script
set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="${HOME}/.claude/settings.json"
HOMUNCULUS_DIR="${HOME}/.claude/homunculus"

YELLOW='\033[1;33m'
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo "continuous-learning-homunculus uninstall"
echo "─────────────────────────────────"
echo ""

# ── Remove hooks from settings.json ───────────────────────────────────────

if [ -f "$SETTINGS_FILE" ]; then
  python3 - "$SETTINGS_FILE" "$SKILL_DIR" <<'PYEOF'
import json, sys

settings_path = sys.argv[1]
skill_dir = sys.argv[2]

with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.get("hooks", {})
skill_scripts = [
    f"{skill_dir}/hooks/observe.sh",
    f"{skill_dir}/agents/analyze-on-stop.sh",
    f"{skill_dir}/agents/start-observer.sh",
]

def remove_skill_hooks(hook_list):
    cleaned = []
    for entry in hook_list:
        filtered = [
            h for h in entry.get("hooks", [])
            if not any(h.get("command", "").startswith(s) for s in skill_scripts)
        ]
        if filtered:
            entry["hooks"] = filtered
            cleaned.append(entry)
    return cleaned

for event in ["PreToolUse", "PostToolUse", "Stop"]:
    if event in hooks:
        hooks[event] = remove_skill_hooks(hooks[event])
        if not hooks[event]:
            del hooks[event]

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("ok")
PYEOF
  echo -e "${GREEN}✓${NC} settings.json에서 훅 제거 완료"
else
  echo -e "${YELLOW}!${NC} settings.json 없음, 스킵"
fi

# ── Remove slash commands ──────────────────────────────────────────────────

COMMANDS_DIR="${HOME}/.claude/commands"
if [ -f "$COMMANDS_DIR/evolve.md" ]; then
  rm "$COMMANDS_DIR/evolve.md"
  echo -e "${GREEN}✓${NC} /evolve 슬래시 커맨드 제거 완료"
fi

# ── Ask about data ─────────────────────────────────────────────────────────

echo ""
echo -e "${YELLOW}학습 데이터 삭제 여부를 선택하세요:${NC}"
echo "  1) 보관 (기본값)"
echo "  2) 삭제 (~/.claude/homunculus/ 전체)"
echo ""
read -r -p "선택 [1/2]: " choice

case "$choice" in
  2)
    echo ""
    read -r -p "정말 삭제할까요? 복구 불가능합니다. [y/N]: " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
      rm -rf "$HOMUNCULUS_DIR"
      echo -e "${GREEN}✓${NC} ~/.claude/homunculus/ 삭제 완료"
    else
      echo "  취소됨. 데이터 보관."
    fi
    ;;
  *)
    echo -e "${GREEN}✓${NC} 데이터 보관됨: $HOMUNCULUS_DIR"
    ;;
esac

# ── Done ───────────────────────────────────────────────────────────────────

echo ""
echo "─────────────────────────────────"
echo "제거 완료. 스킬 디렉토리는 수동으로 삭제하세요:"
echo "  rm -rf $SKILL_DIR"
echo ""
