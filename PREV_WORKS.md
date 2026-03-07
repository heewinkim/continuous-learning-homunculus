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

---

## 2026-03-07 — apply 커맨드 + rule 진화 타입 추가

### 변경 내용

#### 흐름 재설계
- evolved/ 폴더는 자동 스테이징 영역
- `/evolve` 슬래시 커맨드: staged 항목 목록 보여주고 apply 안내 (분석·생성 역할 제거)
- `apply` CLI 커맨드: 터미널에서 직접 실행, 항목별 y/n 선택 후 `~/.claude/`에 배포

#### `scripts/instinct-cli.py`
- `cmd_apply()` 추가 — evolved/ 하위 skills/commands/agents/rules 스캔, 항목별 y/n 선택 적용
  - `--list`: 목록만 출력
  - `--force`: 이미 적용된 항목도 재선택 가능
- `rule` 타입 지원 추가 (클러스터링 프롬프트 + `_generate_evolved_v2`)
- `_claude_update_rule()` 추가 — 기존 `~/.claude/rules/` 파일 읽어 병합·업데이트 (추가 아님)
  - "simple is best" 원칙: 최대 10줄, 권장 3~5줄
  - 모순 신호 → 더 강한 쪽으로 업데이트
- `CLAUDE_RULES_DIR` 모듈 레벨 추가
- `evolved/rules/` 디렉토리 초기화 추가

#### `commands/evolve.md`
- staged 항목 확인 + apply 안내로 역할 변경 (기존 분석·생성 흐름 제거)

#### `setup.sh`
- `evolved/rules/` 디렉토리 생성 추가
- CLI 사용법 메시지 apply 반영

#### `README.md` / `SKILL.md`
- 흐름도 업데이트 (staged → apply → ~/.claude/)
- rule 타입 설명 추가
- CLI 예시 업데이트

### 커밋

- `(이번 세션)` feat: apply command + rule evolution type with simple-is-best principle
