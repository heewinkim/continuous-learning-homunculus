#!/usr/bin/env python3
"""
Instinct CLI - Manage instincts for Continuous Learning v2

Commands:
  status   - Show all instincts and their status
  import   - Import instincts from file or URL
  export   - Export instincts to file
  evolve   - Cluster instincts into skills/commands/agents
"""

import argparse
import json
import os
import sys
import re
import urllib.request
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

HOMUNCULUS_DIR = Path.home() / ".claude" / "homunculus"
INSTINCTS_DIR = HOMUNCULUS_DIR / "instincts"
PERSONAL_DIR = INSTINCTS_DIR / "personal"
INHERITED_DIR = INSTINCTS_DIR / "inherited"
EVOLVED_DIR = HOMUNCULUS_DIR / "evolved"
OBSERVATIONS_FILE = HOMUNCULUS_DIR / "observations.jsonl"

CLAUDE_RULES_DIR = Path.home() / ".claude" / "rules"

# Ensure directories exist
for d in [PERSONAL_DIR, INHERITED_DIR, EVOLVED_DIR / "skills", EVOLVED_DIR / "commands", EVOLVED_DIR / "agents", EVOLVED_DIR / "rules"]:
    d.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# Instinct Parser
# ─────────────────────────────────────────────

def parse_instinct_file(content: str) -> list[dict]:
    """Parse YAML-like instinct file format."""
    instincts = []
    current = {}
    in_frontmatter = False
    content_lines = []

    for line in content.split('\n'):
        if line.strip() == '---':
            if in_frontmatter:
                # End of frontmatter - content comes next, don't append yet
                in_frontmatter = False
            else:
                # Start of frontmatter
                in_frontmatter = True
                if current:
                    current['content'] = '\n'.join(content_lines).strip()
                    instincts.append(current)
                current = {}
                content_lines = []
        elif in_frontmatter:
            # Parse YAML-like frontmatter
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == 'confidence':
                    current[key] = float(value)
                else:
                    current[key] = value
        else:
            content_lines.append(line)

    # Don't forget the last instinct
    if current:
        current['content'] = '\n'.join(content_lines).strip()
        instincts.append(current)

    return [i for i in instincts if i.get('id')]


def load_all_instincts() -> list[dict]:
    """Load all instincts from personal and inherited directories."""
    instincts = []

    for directory in [PERSONAL_DIR, INHERITED_DIR]:
        if not directory.exists():
            continue
        yaml_files = sorted(
            set(directory.glob("*.yaml"))
            | set(directory.glob("*.yml"))
            | set(directory.glob("*.md"))
        )
        for file in yaml_files:
            try:
                content = file.read_text()
                parsed = parse_instinct_file(content)
                for inst in parsed:
                    inst['_source_file'] = str(file)
                    inst['_source_type'] = directory.name
                instincts.extend(parsed)
            except Exception as e:
                print(f"Warning: Failed to parse {file}: {e}", file=sys.stderr)

    return instincts


# ─────────────────────────────────────────────
# Status Command
# ─────────────────────────────────────────────

def cmd_status(args):
    """Show status of all instincts."""
    instincts = load_all_instincts()

    if not instincts:
        print("No instincts found.")
        print(f"\nInstinct directories:")
        print(f"  Personal:  {PERSONAL_DIR}")
        print(f"  Inherited: {INHERITED_DIR}")
        return

    # Group by domain
    by_domain = defaultdict(list)
    for inst in instincts:
        domain = inst.get('domain', 'general')
        by_domain[domain].append(inst)

    # Print header
    print(f"\n{'='*60}")
    print(f"  INSTINCT STATUS - {len(instincts)} total")
    print(f"{'='*60}\n")

    # Summary by source
    personal = [i for i in instincts if i.get('_source_type') == 'personal']
    inherited = [i for i in instincts if i.get('_source_type') == 'inherited']
    print(f"  Personal:  {len(personal)}")
    print(f"  Inherited: {len(inherited)}")
    print()

    # Print by domain
    for domain in sorted(by_domain.keys()):
        domain_instincts = by_domain[domain]
        print(f"## {domain.upper()} ({len(domain_instincts)})")
        print()

        for inst in sorted(domain_instincts, key=lambda x: -x.get('confidence', 0.5)):
            conf = inst.get('confidence', 0.5)
            conf_bar = '█' * int(conf * 10) + '░' * (10 - int(conf * 10))
            trigger = inst.get('trigger', 'unknown trigger')
            source = inst.get('source', 'unknown')

            print(f"  {conf_bar} {int(conf*100):3d}%  {inst.get('id', 'unnamed')}")
            print(f"            trigger: {trigger}")

            # Extract action from content
            content = inst.get('content', '')
            action_match = re.search(r'## Action\s*\n\s*(.+?)(?:\n\n|\n##|$)', content, re.DOTALL)
            if action_match:
                action = action_match.group(1).strip().split('\n')[0]
                print(f"            action: {action[:60]}{'...' if len(action) > 60 else ''}")

            print()

    # Observations stats
    if OBSERVATIONS_FILE.exists():
        obs_count = sum(1 for _ in open(OBSERVATIONS_FILE))
        print(f"─────────────────────────────────────────────────────────")
        print(f"  Observations: {obs_count} events logged")
        print(f"  File: {OBSERVATIONS_FILE}")

    print(f"\n{'='*60}\n")


# ─────────────────────────────────────────────
# Import Command
# ─────────────────────────────────────────────

def cmd_import(args):
    """Import instincts from file or URL."""
    source = args.source

    # Fetch content
    if source.startswith('http://') or source.startswith('https://'):
        print(f"Fetching from URL: {source}")
        try:
            with urllib.request.urlopen(source) as response:
                content = response.read().decode('utf-8')
        except Exception as e:
            print(f"Error fetching URL: {e}", file=sys.stderr)
            return 1
    else:
        path = Path(source).expanduser()
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        content = path.read_text()

    # Parse instincts
    new_instincts = parse_instinct_file(content)
    if not new_instincts:
        print("No valid instincts found in source.")
        return 1

    print(f"\nFound {len(new_instincts)} instincts to import.\n")

    # Load existing
    existing = load_all_instincts()
    existing_ids = {i.get('id') for i in existing}

    # Categorize
    to_add = []
    duplicates = []
    to_update = []

    for inst in new_instincts:
        inst_id = inst.get('id')
        if inst_id in existing_ids:
            # Check if we should update
            existing_inst = next((e for e in existing if e.get('id') == inst_id), None)
            if existing_inst:
                if inst.get('confidence', 0) > existing_inst.get('confidence', 0):
                    to_update.append(inst)
                else:
                    duplicates.append(inst)
        else:
            to_add.append(inst)

    # Filter by minimum confidence
    min_conf = args.min_confidence or 0.0
    to_add = [i for i in to_add if i.get('confidence', 0.5) >= min_conf]
    to_update = [i for i in to_update if i.get('confidence', 0.5) >= min_conf]

    # Display summary
    if to_add:
        print(f"NEW ({len(to_add)}):")
        for inst in to_add:
            print(f"  + {inst.get('id')} (confidence: {inst.get('confidence', 0.5):.2f})")

    if to_update:
        print(f"\nUPDATE ({len(to_update)}):")
        for inst in to_update:
            print(f"  ~ {inst.get('id')} (confidence: {inst.get('confidence', 0.5):.2f})")

    if duplicates:
        print(f"\nSKIP ({len(duplicates)} - already exists with equal/higher confidence):")
        for inst in duplicates[:5]:
            print(f"  - {inst.get('id')}")
        if len(duplicates) > 5:
            print(f"  ... and {len(duplicates) - 5} more")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        return 0

    if not to_add and not to_update:
        print("\nNothing to import.")
        return 0

    # Confirm
    if not args.force:
        response = input(f"\nImport {len(to_add)} new, update {len(to_update)}? [y/N] ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0

    # Write to inherited directory
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    source_name = Path(source).stem if not source.startswith('http') else 'web-import'
    output_file = INHERITED_DIR / f"{source_name}-{timestamp}.yaml"

    all_to_write = to_add + to_update
    output_content = f"# Imported from {source}\n# Date: {datetime.now().isoformat()}\n\n"

    for inst in all_to_write:
        output_content += "---\n"
        output_content += f"id: {inst.get('id')}\n"
        output_content += f"trigger: \"{inst.get('trigger', 'unknown')}\"\n"
        output_content += f"confidence: {inst.get('confidence', 0.5)}\n"
        output_content += f"domain: {inst.get('domain', 'general')}\n"
        output_content += f"source: inherited\n"
        output_content += f"imported_from: \"{source}\"\n"
        if inst.get('source_repo'):
            output_content += f"source_repo: {inst.get('source_repo')}\n"
        output_content += "---\n\n"
        output_content += inst.get('content', '') + "\n\n"

    output_file.write_text(output_content)

    print(f"\n✅ Import complete!")
    print(f"   Added: {len(to_add)}")
    print(f"   Updated: {len(to_update)}")
    print(f"   Saved to: {output_file}")

    return 0


# ─────────────────────────────────────────────
# Export Command
# ─────────────────────────────────────────────

def cmd_export(args):
    """Export instincts to file."""
    instincts = load_all_instincts()

    if not instincts:
        print("No instincts to export.")
        return 1

    # Filter by domain if specified
    if args.domain:
        instincts = [i for i in instincts if i.get('domain') == args.domain]

    # Filter by minimum confidence
    if args.min_confidence:
        instincts = [i for i in instincts if i.get('confidence', 0.5) >= args.min_confidence]

    if not instincts:
        print("No instincts match the criteria.")
        return 1

    # Generate output
    output = f"# Instincts export\n# Date: {datetime.now().isoformat()}\n# Total: {len(instincts)}\n\n"

    for inst in instincts:
        output += "---\n"
        for key in ['id', 'trigger', 'confidence', 'domain', 'source', 'source_repo']:
            if inst.get(key):
                value = inst[key]
                if key == 'trigger':
                    output += f'{key}: "{value}"\n'
                else:
                    output += f"{key}: {value}\n"
        output += "---\n\n"
        output += inst.get('content', '') + "\n\n"

    # Write to file or stdout
    if args.output:
        Path(args.output).write_text(output)
        print(f"Exported {len(instincts)} instincts to {args.output}")
    else:
        print(output)

    return 0


# ─────────────────────────────────────────────
# Claude Semantic Clustering
# ─────────────────────────────────────────────

def _claude_cluster_instincts(instincts: list) -> list:
    """Use Claude Haiku to semantically cluster instincts."""
    import subprocess

    if not instincts:
        return []

    lines = []
    for inst in instincts:
        lines.append(
            f"- id: {inst.get('id')}, domain: {inst.get('domain', 'general')}, "
            f"confidence: {inst.get('confidence', 0.5):.2f}, trigger: {inst.get('trigger', '')}"
        )
    instinct_list = '\n'.join(lines)

    prompt = f"""Analyze these learned instincts and group semantically related ones into clusters.

INSTINCTS:
{instinct_list}

Group instincts into clusters where each cluster:
- Contains 2+ thematically related instincts
- Would form a cohesive skill, command, or agent
- Has a clear unified purpose

Output ONLY valid JSON (no markdown, no explanation):
{{
  "clusters": [
    {{
      "name": "kebab-case-name",
      "theme": "one sentence describing what this cluster is about",
      "type": "skill|command|agent",
      "instinct_ids": ["id1", "id2"]
    }}
  ]
}}

type rules:
- skill: reusable knowledge/approach pattern (2+ instincts)
- command: a workflow that can be invoked as a slash command
- agent: complex specialization requiring 3+ high-confidence instincts
- rule: a core behavioral principle about the user's values/philosophy/communication style (2+ high-confidence instincts). Will UPDATE existing rules, not add new ones.

If no meaningful clusters exist, return {{"clusters": []}}"""

    env = {**os.environ}
    env.pop('CLAUDECODE', None)

    try:
        result = subprocess.run(
            ['claude', '--model', 'haiku', '--max-turns', '1', '--print', prompt],
            capture_output=True, text=True, env=env, timeout=60
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Warning: Claude unavailable ({e})", file=sys.stderr)
        return []

    if result.returncode != 0:
        print(f"Warning: Claude error: {result.stderr[:200]}", file=sys.stderr)
        return []

    output = result.stdout.strip()
    json_match = re.search(r'\{[\s\S]*\}', output)
    if not json_match:
        print(f"Warning: No JSON in Claude output", file=sys.stderr)
        return []

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"Warning: JSON parse error: {e}", file=sys.stderr)
        return []

    id_to_inst = {i.get('id'): i for i in instincts}
    clusters = []
    for cluster in data.get('clusters', []):
        resolved = [id_to_inst[iid] for iid in cluster.get('instinct_ids', []) if iid in id_to_inst]
        if len(resolved) < 2:
            continue
        clusters.append({
            'name': cluster.get('name', 'unnamed'),
            'theme': cluster.get('theme', ''),
            'type': cluster.get('type', 'skill'),
            'instincts': resolved,
            'avg_confidence': sum(i.get('confidence', 0.5) for i in resolved) / len(resolved),
        })

    return clusters


def _claude_update_rule(name: str, theme: str, instincts: list, existing_content: str) -> str:
    """Use Claude Haiku to generate or update a rule file, merging existing content with new instincts."""
    import subprocess

    instinct_lines = '\n'.join(
        f"- {i.get('trigger', i.get('id', ''))}: {i.get('content', '')[:200]}"
        for i in instincts
    )

    existing_section = f"EXISTING RULE CONTENT:\n---\n{existing_content}\n---\n" if existing_content else "EXISTING RULE CONTENT: (none — create new)\n"

    prompt = f"""You are updating a Claude Code rule file.

{existing_section}
NEW INSTINCTS TO INCORPORATE:
{instinct_lines}

Write an updated rule file for "{name}" ({theme}).

STRICT PRINCIPLES:
- Simple is best. Fewer rules = higher accuracy.
- Keep only the most essential, actionable principles.
- If new instincts contradict existing rules, update the rule to reflect the stronger signal.
- If new instincts reinforce existing rules, keep the rule concise — do not add redundant lines.
- Maximum 10 lines of actual content. Prefer 3-5.
- Output ONLY the raw markdown content of the rule file. No explanation."""

    env = {**os.environ}
    env.pop('CLAUDECODE', None)

    try:
        result = subprocess.run(
            ['claude', '--model', 'haiku', '--max-turns', '1', '--print', prompt],
            capture_output=True, text=True, env=env, timeout=60
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return existing_content  # fallback: keep existing

    output = result.stdout.strip()
    return output if output else existing_content


# ─────────────────────────────────────────────
# Evolve Command
# ─────────────────────────────────────────────

def cmd_evolve(args):
    """Analyze instincts and suggest evolutions to skills/commands/agents."""
    instincts = load_all_instincts()

    if len(instincts) < 3:
        print("Need at least 3 instincts to analyze patterns.")
        print(f"Currently have: {len(instincts)}")
        return 1

    print(f"\n{'='*60}")
    print(f"  EVOLVE ANALYSIS - {len(instincts)} instincts")
    print(f"{'='*60}\n")

    high_conf = [i for i in instincts if i.get('confidence', 0) >= 0.8]
    print(f"High confidence instincts (>=80%): {len(high_conf)}")

    print("\nClaude Haiku로 의미론적 클러스터링 중...")
    clusters = _claude_cluster_instincts(instincts)

    print(f"\nSemantic clusters found: {len(clusters)}")

    if clusters:
        skill_clusters = [c for c in clusters if c['type'] == 'skill']
        cmd_clusters = [c for c in clusters if c['type'] == 'command']
        agent_clusters = [c for c in clusters if c['type'] == 'agent']

        if skill_clusters:
            print(f"\n## SKILL CANDIDATES ({len(skill_clusters)})\n")
            for i, c in enumerate(skill_clusters, 1):
                print(f"{i}. {c['name']}")
                print(f"   Theme: {c['theme']}")
                print(f"   Instincts ({len(c['instincts'])}): {', '.join(inst.get('id') for inst in c['instincts'])}")
                print(f"   Avg confidence: {c['avg_confidence']:.0%}")
                print()

        if cmd_clusters:
            print(f"\n## COMMAND CANDIDATES ({len(cmd_clusters)})\n")
            for c in cmd_clusters:
                print(f"  /{c['name']}")
                print(f"   Theme: {c['theme']}")
                print(f"   Instincts: {', '.join(inst.get('id') for inst in c['instincts'])}")
                print()

        if agent_clusters:
            print(f"\n## AGENT CANDIDATES ({len(agent_clusters)})\n")
            for c in agent_clusters:
                print(f"  {c['name']}-agent")
                print(f"   Theme: {c['theme']}")
                print(f"   Covers {len(c['instincts'])} instincts, avg confidence: {c['avg_confidence']:.0%}")
                print()

    if args.generate:
        if not clusters:
            print("\nNo clusters to generate from.")
        else:
            generated = _generate_evolved_v2(clusters)
            if generated:
                print(f"\nGenerated {len(generated)} evolved structures:")
                for path in generated:
                    print(f"   {path}")
            else:
                print("\nNo structures generated (need higher-confidence clusters).")

    print(f"\n{'='*60}\n")
    return 0


# ─────────────────────────────────────────────
# Generate Evolved Structures (v2 - semantic clusters)
# ─────────────────────────────────────────────

def _generate_evolved_v2(clusters: list) -> list[str]:
    """Generate skill/command/agent files from semantic clusters."""
    generated = []

    for cluster in clusters:
        name = re.sub(r'[^a-z0-9]+', '-', cluster['name'].lower()).strip('-')[:30]
        if not name:
            continue
        ctype = cluster['type']
        theme = cluster['theme']
        inst_list = cluster['instincts']
        avg_conf = cluster['avg_confidence']

        if ctype == 'skill':
            skill_dir = EVOLVED_DIR / "skills" / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            content = f"---\nname: {name}\ndescription: {theme}\n---\n\n"
            content += f"# {name}\n\n{theme}\n\n"
            content += f"Evolved from {len(inst_list)} instincts (avg confidence: {avg_conf:.0%})\n\n"
            content += "## When to Apply\n\n"
            for inst in inst_list:
                content += f"- {inst.get('trigger', inst.get('id'))}\n"
            content += "\n## Actions\n\n"
            for inst in inst_list:
                inst_content = inst.get('content', '')
                practice = re.search(r'## In Practice\s*\n\s*(.+?)(?:\n\n|\n##|$)', inst_content, re.DOTALL)
                action = re.search(r'## Action\s*\n\s*(.+?)(?:\n\n|\n##|$)', inst_content, re.DOTALL)
                m = practice or action
                text = m.group(1).strip().split('\n')[0] if m else inst.get('id', 'unnamed')
                content += f"- **{inst.get('id')}**: {text[:80]}\n"
            path = skill_dir / "SKILL.md"
            path.write_text(content)
            generated.append(str(path))

        elif ctype == 'command':
            cmd_file = EVOLVED_DIR / "commands" / f"{name}.md"
            content = f"# {name}\n\n{theme}\n\nConfidence: {avg_conf:.0%}\n\n"
            for inst in inst_list:
                content += f"## {inst.get('id', 'unnamed')}\n\n"
                content += inst.get('content', '') + "\n\n"
            cmd_file.write_text(content)
            generated.append(str(cmd_file))

        elif ctype == 'agent':
            agent_file = EVOLVED_DIR / "agents" / f"{name}.md"
            domains = ', '.join(set(i.get('domain', 'general') for i in inst_list))
            content = "---\nmodel: sonnet\ntools: Read, Grep, Glob, Edit, Bash\n---\n\n"
            content += f"# {name}\n\n{theme}\n\n"
            content += f"Evolved from {len(inst_list)} instincts (avg confidence: {avg_conf:.0%})\n"
            content += f"Domains: {domains}\n\n"
            content += "## Source Instincts\n\n"
            for inst in inst_list:
                content += f"- **{inst.get('id')}**: {inst.get('trigger', '')}\n"
            agent_file.write_text(content)
            generated.append(str(agent_file))

        elif ctype == 'rule':
            rule_file = EVOLVED_DIR / "rules" / f"{name}.md"
            existing_rule = CLAUDE_RULES_DIR / f"{name}.md"
            existing_content = existing_rule.read_text() if existing_rule.exists() else ""
            print(f"  규칙 업데이트 중: {name} ({'기존 규칙 병합' if existing_content else '신규 생성'})...")
            updated = _claude_update_rule(name, theme, inst_list, existing_content)
            rule_file.write_text(updated)
            generated.append(str(rule_file))

    return generated


# ─────────────────────────────────────────────
# Generate Evolved Structures (legacy)
# ─────────────────────────────────────────────

def _generate_evolved(skill_candidates: list, workflow_instincts: list, agent_candidates: list) -> list[str]:
    """Generate skill/command/agent files from analyzed instinct clusters."""
    generated = []

    # Generate skills from top candidates
    for cand in skill_candidates[:5]:
        trigger = cand['trigger'].strip()
        if not trigger:
            continue
        name = re.sub(r'[^a-z0-9]+', '-', trigger.lower()).strip('-')[:30]
        if not name:
            continue

        skill_dir = EVOLVED_DIR / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        content = f"# {name}\n\n"
        content += f"Evolved from {len(cand['instincts'])} instincts "
        content += f"(avg confidence: {cand['avg_confidence']:.0%})\n\n"
        content += f"## When to Apply\n\n"
        content += f"Trigger: {trigger}\n\n"
        content += f"## Actions\n\n"
        for inst in cand['instincts']:
            inst_content = inst.get('content', '')
            action_match = re.search(r'## Action\s*\n\s*(.+?)(?:\n\n|\n##|$)', inst_content, re.DOTALL)
            action = action_match.group(1).strip() if action_match else inst.get('id', 'unnamed')
            content += f"- {action}\n"

        (skill_dir / "SKILL.md").write_text(content)
        generated.append(str(skill_dir / "SKILL.md"))

    # Generate commands from workflow instincts
    for inst in workflow_instincts[:5]:
        trigger = inst.get('trigger', 'unknown')
        cmd_name = re.sub(r'[^a-z0-9]+', '-', trigger.lower().replace('when ', '').replace('implementing ', ''))
        cmd_name = cmd_name.strip('-')[:20]
        if not cmd_name:
            continue

        cmd_file = EVOLVED_DIR / "commands" / f"{cmd_name}.md"
        content = f"# {cmd_name}\n\n"
        content += f"Evolved from instinct: {inst.get('id', 'unnamed')}\n"
        content += f"Confidence: {inst.get('confidence', 0.5):.0%}\n\n"
        content += inst.get('content', '')

        cmd_file.write_text(content)
        generated.append(str(cmd_file))

    # Generate agents from complex clusters
    for cand in agent_candidates[:3]:
        trigger = cand['trigger'].strip()
        agent_name = re.sub(r'[^a-z0-9]+', '-', trigger.lower()).strip('-')[:20]
        if not agent_name:
            continue

        agent_file = EVOLVED_DIR / "agents" / f"{agent_name}.md"
        domains = ', '.join(cand['domains'])
        instinct_ids = [i.get('id', 'unnamed') for i in cand['instincts']]

        content = f"---\nmodel: sonnet\ntools: Read, Grep, Glob\n---\n"
        content += f"# {agent_name}\n\n"
        content += f"Evolved from {len(cand['instincts'])} instincts "
        content += f"(avg confidence: {cand['avg_confidence']:.0%})\n"
        content += f"Domains: {domains}\n\n"
        content += f"## Source Instincts\n\n"
        for iid in instinct_ids:
            content += f"- {iid}\n"

        agent_file.write_text(content)
        generated.append(str(agent_file))

    return generated


# ─────────────────────────────────────────────
# Apply Command
# ─────────────────────────────────────────────

CLAUDE_DIR = Path.home() / ".claude"

APPLY_TARGETS = {
    "skill":   (EVOLVED_DIR / "skills",   CLAUDE_DIR / "skills"),
    "command": (EVOLVED_DIR / "commands", CLAUDE_DIR / "commands"),
    "agent":   (EVOLVED_DIR / "agents",   CLAUDE_DIR / "agents"),
}


def cmd_apply(args):
    """Show evolved items and selectively apply them to ~/.claude/."""
    candidates = []

    # skills: each subdirectory with SKILL.md
    evolved_skills = EVOLVED_DIR / "skills"
    if evolved_skills.exists():
        for skill_dir in sorted(evolved_skills.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if skill_dir.is_dir() and skill_file.exists():
                dest = CLAUDE_DIR / "skills" / skill_dir.name / "SKILL.md"
                candidates.append({
                    "type": "skill",
                    "name": skill_dir.name,
                    "src": skill_file,
                    "dest": dest,
                    "applied": dest.exists(),
                })

    # commands: .md files
    evolved_commands = EVOLVED_DIR / "commands"
    if evolved_commands.exists():
        for cmd_file in sorted(evolved_commands.glob("*.md")):
            dest = CLAUDE_DIR / "commands" / cmd_file.name
            candidates.append({
                "type": "command",
                "name": cmd_file.stem,
                "src": cmd_file,
                "dest": dest,
                "applied": dest.exists(),
            })

    # agents: .md files
    evolved_agents = EVOLVED_DIR / "agents"
    if evolved_agents.exists():
        for agent_file in sorted(evolved_agents.glob("*.md")):
            dest = CLAUDE_DIR / "agents" / agent_file.name
            candidates.append({
                "type": "agent",
                "name": agent_file.stem,
                "src": agent_file,
                "dest": dest,
                "applied": dest.exists(),
            })

    # rules: .md files → ~/.claude/rules/ (update, not add)
    evolved_rules = EVOLVED_DIR / "rules"
    if evolved_rules.exists():
        for rule_file in sorted(evolved_rules.glob("*.md")):
            dest = CLAUDE_RULES_DIR / rule_file.name
            candidates.append({
                "type": "rule",
                "name": rule_file.stem,
                "src": rule_file,
                "dest": dest,
                "applied": dest.exists(),
                "is_update": dest.exists(),
            })

    if not candidates:
        print("No evolved items found. Run 'evolve --generate' first.")
        return 1

    print(f"\n{'='*60}")
    print(f"  EVOLVED ITEMS — {len(candidates)} total")
    print(f"{'='*60}\n")

    for i, c in enumerate(candidates, 1):
        if c["type"] == "rule":
            status = "[UPDATE existing rule]" if c.get("is_update") else "[NEW rule]"
        else:
            status = "[already applied]" if c["applied"] else "[not applied]"
        print(f"  {i}. [{c['type']}] {c['name']}  {status}")
        # Show first non-empty content line as description
        try:
            for line in c["src"].read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('---') and ':' not in line[:20]:
                    print(f"     → {line[:80]}")
                    break
        except Exception:
            pass
        print()

    if args.list:
        return 0

    print("각 항목을 적용할지 선택해줘. (y=적용, n=건너뜀, q=종료)\n")

    applied = []
    for c in candidates:
        tag = f"[{c['type']}] {c['name']}"
        if c["applied"] and not args.force:
            print(f"  {tag} → 이미 적용됨, 건너뜀 (--force로 덮어쓸 수 있어)")
            continue

        try:
            answer = input(f"  {tag} 적용? [y/N/q] ").strip().lower()
        except EOFError:
            answer = 'n'

        if answer == 'q':
            print("중단.")
            break
        if answer != 'y':
            continue

        c["dest"].parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(c["src"], c["dest"])
        print(f"  ✓ {c['dest']}")
        applied.append(c)

    print(f"\n적용 완료: {len(applied)}개")
    if applied:
        print("다음 Claude Code 세션부터 반영돼!")
    print()
    return 0


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Instinct CLI for Continuous Learning v2')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Status
    status_parser = subparsers.add_parser('status', help='Show instinct status')

    # Import
    import_parser = subparsers.add_parser('import', help='Import instincts')
    import_parser.add_argument('source', help='File path or URL')
    import_parser.add_argument('--dry-run', action='store_true', help='Preview without importing')
    import_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    import_parser.add_argument('--min-confidence', type=float, help='Minimum confidence threshold')

    # Export
    export_parser = subparsers.add_parser('export', help='Export instincts')
    export_parser.add_argument('--output', '-o', help='Output file')
    export_parser.add_argument('--domain', help='Filter by domain')
    export_parser.add_argument('--min-confidence', type=float, help='Minimum confidence')

    # Evolve
    evolve_parser = subparsers.add_parser('evolve', help='Analyze and evolve instincts')
    evolve_parser.add_argument('--generate', action='store_true', help='Generate evolved structures')

    # Apply
    apply_parser = subparsers.add_parser('apply', help='Selectively apply evolved items to ~/.claude/')
    apply_parser.add_argument('--list', action='store_true', help='Just list, do not prompt')
    apply_parser.add_argument('--force', action='store_true', help='Re-apply already applied items')

    args = parser.parse_args()

    if args.command == 'status':
        return cmd_status(args)
    elif args.command == 'import':
        return cmd_import(args)
    elif args.command == 'export':
        return cmd_export(args)
    elif args.command == 'evolve':
        return cmd_evolve(args)
    elif args.command == 'apply':
        return cmd_apply(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
