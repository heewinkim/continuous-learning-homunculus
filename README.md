# continuous-learning-homunculus

Claude Code가 세션을 관찰하고, 당신의 **행동·철학·습관**을 atomic "instinct"로 학습하는 시스템.

코딩 패턴을 배우는 게 아니라 — 당신이 어떤 사람인지를 배운다.

```
세션 활동
    │
    │  PreToolUse/PostToolUse 훅 (100% 신뢰도)
    ▼
observations.jsonl
    │
    │  세션 종료 시 (Stop 훅) → Claude Haiku 분석
    ▼
instincts/personal/
    ├── prefers-direct-over-safe.md      (confidence: 0.8)
    ├── values-simplicity-in-design.md   (confidence: 0.7)
    └── dislikes-over-explanation.md     (confidence: 0.65)
    │
    │  /evolve
    ▼
evolved/skills/, evolved/commands/, evolved/agents/
```

## 무엇을 배우는가

툴 사용 패턴이 아니라 사람 자체를 학습한다:

| 패턴 | 무엇을 발견하는가 |
|------|-----------------|
| `value_corrections` | 어떤 가치관이 행동을 이끄는가 |
| `aesthetic_standards` | 이 사람의 '좋다'의 기준이 뭔가 |
| `decision_philosophy` | 선택 뒤에 어떤 원칙이 있는가 |
| `communication_preferences` | 어떤 방식으로 대화받길 원하는가 |
| `avoidance_patterns` | 뭘 일관되게 싫어하는가 |
| `curiosity_areas` | 무엇이 계속 당기는가 |
| `work_rhythm` | 어떻게 자연스럽게 일하는가 |
| `expression_style` | 어떻게 생각을 표현하는가 |
| `priority_patterns` | 긴장 상황에서 뭘 먼저 두는가 |
| `problem_approach` | 어려운 상황에서 어떻게 반응하는가 |

## 설치

```bash
git clone https://github.com/YOUR_USERNAME/continuous-learning-homunculus ~/.claude/skills/continuous-learning-homunculus
cd ~/.claude/skills/continuous-learning-homunculus
bash setup.sh
```

## 동작 방식

### 1. 관찰 (항상 켜짐)

PreToolUse / PostToolUse 훅이 모든 툴 호출을 `~/.claude/homunculus/observations.jsonl`에 기록한다. 확률적이 아니라 100% 실행.

### 2. 분석 (세션 종료 시)

Stop 훅이 세션 종료를 감지하면 `analyze-on-stop.sh`가 실행된다. Claude Haiku가 쌓인 observations을 읽고 패턴을 찾아 instinct 파일을 생성한다.

24/7 백그라운드 데몬 없음 — 일하지 않는 시간엔 아무것도 실행되지 않는다.

### 3. Instinct 파일

```yaml
---
id: values-directness-over-safety
trigger: "when presenting options or solutions"
confidence: 0.75
domain: values
source: session-observation
---

# Values Directness Over Safety

## Insight
This person consistently pushes back when Claude hedges or softens conclusions. They prefer a direct, confident take even if it's occasionally wrong.

## In Practice
Skip disclaimers and qualifications. State the recommendation first, reasoning second. Don't offer multiple options when one is clearly better.

## Evidence
- Observed 6 times
- Last observed: 2026-02-25
```

### 4. CLI

```bash
python3 ~/.claude/skills/continuous-learning-homunculus/scripts/instinct-cli.py status
python3 ~/.claude/skills/continuous-learning-homunculus/scripts/instinct-cli.py export -o my-instincts.yaml
python3 ~/.claude/skills/continuous-learning-homunculus/scripts/instinct-cli.py import friend-instincts.yaml
python3 ~/.claude/skills/continuous-learning-homunculus/scripts/instinct-cli.py evolve --generate
```

## 파일 구조

```
~/.claude/skills/continuous-learning-homunculus/
├── hooks/
│   └── observe.sh              # PreToolUse/PostToolUse 훅
├── agents/
│   ├── analyze-on-stop.sh      # Stop 훅 분석 스크립트
│   ├── start-observer.sh       # 데몬 방식 (선택적)
│   └── observer.md             # Observer agent 스펙
├── scripts/
│   ├── instinct-cli.py         # CLI 도구
│   └── test_parse_instinct.py  # 테스트
├── config.json
├── SKILL.md
└── README.md

~/.claude/homunculus/           # 런타임 데이터 (gitignore됨)
├── observations.jsonl
├── observations.archive/
├── instincts/
│   ├── personal/               # 자동 학습된 instinct
│   └── inherited/              # 다른 사람에게서 가져온 instinct
└── evolved/
    ├── skills/
    ├── commands/
    └── agents/
```

## 설정

`config.json`에서 조정:

```json
{
  "observer": {
    "enabled": true,
    "model": "haiku",
    "trigger_mode": "session_end",
    "min_observations_to_analyze": 20
  }
}
```

`min_observations_to_analyze` — 이 수치 미만이면 분석 스킵. 짧은 세션에서 노이즈 방지.

## Confidence 기준

| 점수 | 의미 |
|------|------|
| 0.3 | 한두 번 관찰됨, 가설 수준 |
| 0.5 | 반복 확인됨, 적용 고려 |
| 0.7 | 강한 패턴, 자동 적용 |
| 0.85+ | 핵심 특성, 거의 확실 |

## Instinct 공유

```bash
# 내 instinct 내보내기
python3 scripts/instinct-cli.py export --min-confidence 0.6 -o my-profile.yaml

# 다른 사람 instinct 가져오기
python3 scripts/instinct-cli.py import https://raw.githubusercontent.com/.../instincts.yaml
```

## 프라이버시

- 모든 데이터는 로컬(`~/.claude/homunculus/`)에만 저장
- observations.jsonl은 git에 포함되지 않음 (`.gitignore`)
- export 시 실제 대화 내용이 아닌 패턴(instinct)만 공유됨

## 제거

```bash
bash ~/.claude/skills/continuous-learning-homunculus/uninstall.sh
```
