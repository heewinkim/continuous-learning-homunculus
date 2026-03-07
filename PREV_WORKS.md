# Previous Works

## 2026-03-07 — evolve 버그 수정 + 자동화

### 문제 발견

1. **`/evolve` 슬래시 커맨드 미등록** — `~/.claude/commands/evolve.md` 파일이 없어서 커맨드 자체가 없었음
2. **클러스터링 로직 버그** — `instinct-cli.py`의 evolve가 trigger 문자열에서 키워드 몇 개만 제거한 뒤 단순 문자열 매칭으로 클러스터를 찾으려 했음. 각 instinct의 trigger가 모두 고유한 긴 문장이라 클러스터가 항상 0개 반환됨

### 해결

#### `scripts/instinct-cli.py`
- 기존 문자열 매칭 클러스터링 제거
- `_claude_cluster_instincts(instincts)` 추가 — Claude Haiku에게 instinct 목록을 넘겨 의미론적으로 유사한 것들을 JSON으로 묶어달라고 요청
- `_generate_evolved_v2(clusters)` 추가 — 새 클러스터 포맷(name, theme, type, instincts)으로 skill/command/agent 파일 생성
- 기존 `_generate_evolved()` 는 legacy로 보존

#### `agents/analyze-on-stop.sh`
- 세션 종료 시 instinct 분석 완료 후 자동으로 `instinct-cli.py evolve --generate` 실행하는 블록 추가

#### `config.json`
- `evolution.auto_evolve`: `false` → `true`

#### `setup.sh`
- `/evolve` 슬래시 커맨드를 `~/.claude/commands/`에 자동 복사하는 단계 추가
- 완료 메시지에 auto-evolve 동작 설명 반영

#### `uninstall.sh`
- 제거 시 `~/.claude/commands/evolve.md` 자동 삭제 추가

#### `commands/evolve.md` (신규)
- 스킬 repo 내에 `/evolve` 커맨드 소스 파일 추가 (setup.sh가 여기서 복사)

#### `README.md` / `SKILL.md`
- auto-evolve 동작, `/evolve` 커맨드, Claude Haiku 클러스터링, `auto_evolve` 설정 항목 반영

### 최종 자동화 흐름

```
세션 종료 (Stop 훅)
    │
    ▼
analyze-on-stop.sh
    ├── observations 분석 → instincts 생성/갱신  (Claude Haiku)
    └── evolve --generate → semantic clustering → skills/commands/agents 생성  (Claude Haiku)
```

### 커밋

- `c28c774` feat: Claude Haiku semantic clustering for evolve + auto-evolve on session end
- `5bc6a5a` feat: setup/uninstall now manages /evolve slash command
