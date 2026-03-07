---
name: continuous-learning-homunculus
description: Instinct-based learning system that observes sessions via hooks, creates atomic instincts with confidence scoring, and evolves them into skills/commands/agents.
version: 2.0.0
---

# Continuous Learning v2 - Instinct-Based Architecture

An advanced learning system that turns your Claude Code sessions into reusable knowledge through atomic "instincts" - small learned behaviors with confidence scoring.

## When to Activate

- Setting up automatic learning from Claude Code sessions
- Configuring instinct-based behavior extraction via hooks
- Tuning confidence thresholds for learned behaviors
- Reviewing, exporting, or importing instinct libraries
- Evolving instincts into full skills, commands, or agents

## What's New in v2

| Feature | v1 | v2 |
|---------|----|----|
| Observation | Stop hook (session end) | PreToolUse/PostToolUse (100% reliable) |
| Analysis | Main context | Background agent (Haiku) |
| Granularity | Full skills | Atomic "instincts" |
| Confidence | None | 0.3-0.9 weighted |
| Clustering | String matching | Claude Haiku semantic clustering |
| Evolution | Manual | Auto on session end (auto_evolve: true) |
| Sharing | None | Export/import instincts |

## The Instinct Model

An instinct is a small learned behavior:

```yaml
---
id: prefer-functional-style
trigger: "when writing new functions"
confidence: 0.7
domain: "code-style"
source: "session-observation"
---

# Prefer Functional Style

## Action
Use functional patterns over classes when appropriate.

## Evidence
- Observed 5 instances of functional pattern preference
- User corrected class-based approach to functional on 2025-01-15
```

**Properties:**
- **Atomic** — one trigger, one action
- **Confidence-weighted** — 0.3 = tentative, 0.9 = near certain
- **Domain-tagged** — code-style, testing, git, debugging, workflow, etc.
- **Evidence-backed** — tracks what observations created it

## How It Works

```
Session Activity
      │
      │ Hooks capture prompts + tool use (100% reliable)
      ▼
┌─────────────────────────────────────────┐
│         observations.jsonl              │
│   (prompts, tool calls, outcomes)       │
└─────────────────────────────────────────┘
      │
      │ Observer agent reads (background, Haiku)
      ▼
┌─────────────────────────────────────────┐
│          PATTERN DETECTION              │
│   • User corrections → instinct         │
│   • Error resolutions → instinct        │
│   • Repeated workflows → instinct       │
└─────────────────────────────────────────┘
      │
      │ Creates/updates
      ▼
┌─────────────────────────────────────────┐
│         instincts/personal/             │
│   • prefer-functional.md (0.7)          │
│   • always-test-first.md (0.9)          │
│   • use-zod-validation.md (0.6)         │
└─────────────────────────────────────────┘
      │
      │ /evolve clusters
      ▼
┌─────────────────────────────────────────┐
│              evolved/                   │
│   • commands/new-feature.md             │
│   • skills/testing-workflow.md          │
│   • agents/refactor-specialist.md       │
└─────────────────────────────────────────┘
```

## Quick Start

### 1. Enable Observation Hooks

Add to your `~/.claude/settings.json`.

**If installed as a plugin** (recommended):

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/skills/continuous-learning-homunculus/hooks/observe.sh pre"
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/skills/continuous-learning-homunculus/hooks/observe.sh post"
      }]
    }]
  }
}
```

**If installed manually** to `~/.claude/skills`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/skills/continuous-learning-homunculus/hooks/observe.sh pre"
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/skills/continuous-learning-homunculus/hooks/observe.sh post"
      }]
    }]
  }
}
```

### 2. Initialize Directory Structure

The Python CLI will create these automatically, but you can also create them manually:

```bash
mkdir -p ~/.claude/homunculus/{instincts/{personal,inherited},evolved/{agents,skills,commands}}
touch ~/.claude/homunculus/observations.jsonl
```

### 3. Use the Instinct Commands

```bash
/instinct-status     # Show learned instincts with confidence scores
/evolve              # Semantically cluster instincts (Claude Haiku) into skills/commands/agents
/instinct-export     # Export instincts for sharing
/instinct-import     # Import instincts from others
```

## Commands

| Command | Description |
|---------|-------------|
| `/instinct-status` | Show all learned instincts with confidence |
| `/evolve` | Cluster related instincts into skills/commands |
| `/instinct-export` | Export instincts for sharing |
| `/instinct-import <file>` | Import instincts from others |

## Configuration

Edit `config.json`:

```json
{
  "version": "2.0",
  "observation": {
    "enabled": true,
    "store_path": "~/.claude/homunculus/observations.jsonl",
    "max_file_size_mb": 10,
    "archive_after_days": 7
  },
  "instincts": {
    "personal_path": "~/.claude/homunculus/instincts/personal/",
    "inherited_path": "~/.claude/homunculus/instincts/inherited/",
    "min_confidence": 0.65,
    "auto_approve_threshold": 0.8,
    "confidence_decay_rate": 0.02,
    "max_instincts": 15
  },
  "observer": {
    "enabled": true,
    "model": "haiku",
    "trigger_mode": "session_end",
    "min_observations_to_analyze": 20,
    "patterns_to_detect": [
      "value_corrections",
      "aesthetic_standards",
      "decision_philosophy",
      "communication_preferences",
      "avoidance_patterns",
      "curiosity_areas",
      "work_rhythm",
      "expression_style",
      "priority_patterns",
      "problem_approach"
    ]
  },
  "evolution": {
    "cluster_threshold": 3,
    "evolved_path": "~/.claude/homunculus/evolved/",
    "auto_evolve": false
  }
}
```

## File Structure

```
~/.claude/homunculus/           # 런타임 데이터 (gitignore됨)
├── observations.jsonl          # 현재 세션 관찰 데이터
├── observations.archive/       # 처리된 관찰 데이터
├── instincts/
│   ├── personal/               # 자동 학습된 instinct
│   └── inherited/              # 다른 사람에게서 가져온 instinct
└── evolved/
    ├── agents/                 # 생성된 전문 에이전트
    ├── skills/                 # 생성된 스킬
    └── commands/               # 생성된 커맨드
```

## Integration with Skill Creator

When you use the [Skill Creator GitHub App](https://skill-creator.app), it now generates **both**:
- Traditional SKILL.md files (for backward compatibility)
- Instinct collections (for v2 learning system)

Instincts from repo analysis have `source: "repo-analysis"` and include the source repository URL.

## Confidence Scoring

Confidence evolves over time:

| Score | Meaning | Behavior |
|-------|---------|----------|
| < 0.65 | Insufficient | Not written — below creation threshold |
| 0.65 | Tentative | Created cautiously, needs reinforcement |
| 0.7 | Moderate | Applied when relevant |
| 0.8 | Strong | Auto-approved for application |
| 0.9 | Near-certain | Core behavior |

**Confidence increases** when:
- Pattern is repeatedly observed
- User doesn't correct the suggested behavior
- Similar instincts from other sources agree

**Confidence decreases** when:
- User explicitly corrects the behavior
- Pattern isn't observed for extended periods
- Contradicting evidence appears

## Why Hooks vs Skills for Observation?

> "v1 relied on skills to observe. Skills are probabilistic—they fire ~50-80% of the time based on Claude's judgment."

Hooks fire **100% of the time**, deterministically. This means:
- Every tool call is observed
- No patterns are missed
- Learning is comprehensive

## Backward Compatibility

v2 is fully compatible with v1:
- Existing `~/.claude/skills/learned/` skills still work
- Stop hook still runs (but now also feeds into v2)
- Gradual migration path: run both in parallel

## Privacy

- Observations stay **local** on your machine
- Only **instincts** (patterns) can be exported
- No actual code or conversation content is shared
- You control what gets exported

## Related

- [Skill Creator](https://skill-creator.app) - Generate instincts from repo history
- [Homunculus](https://github.com/humanplane/continuous-learning-homunculus) - Inspiration for v2 architecture
- [The Longform Guide](https://x.com/affaanmustafa/status/2014040193557471352) - Continuous learning section

---

*Instinct-based learning: teaching Claude your patterns, one observation at a time.*
