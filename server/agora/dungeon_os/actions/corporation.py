"""Corporation actions — Scout, Researcher, Brainmaster, CEO/CTO, Compound.

Each action maps to an agent role in the Autonomous Agent Corporation:
  - Scout: scans GitHub for trending topics, Phaser releases
  - Researcher: reads URLs, synthesizes findings (3 parallel variants)
  - Brainmaster: stores structured knowledge to vault
  - CEO/CTO: evaluates proposals, adversarial filtering
  - Compound: extracts lessons, writes MEMORY.md
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from agora.dungeon_os.actions.role_prompts import get_role_prompt


# ═══════════════════════════════════════════
# SCOUT — Horizon Scanner
# ═══════════════════════════════════════════

async def action_scan_horizon(config: dict, quest: dict, params: dict) -> dict:
    """Scan GitHub for trending topics and Phaser releases.

    Uses GitHub API to check:
      - Phaser releases for latest version + features
      - Trending TypeScript repos
      - Specific topics from STRATEGY.md

    Returns a list of findings with relevance scores.
    """
    log_dir = config.get("log_dir", "/tmp/hermes-logs")
    os.makedirs(log_dir, exist_ok=True)

    findings = []

    # 1. Check Phaser releases
    phaser_result = _check_phaser_releases()
    if phaser_result:
        findings.append(phaser_result)

    # 2. Check GitHub trending (TypeScript)
    trending = _check_trending()
    findings.extend(trending)

    # 3. Score and sort by relevance
    for f in findings:
        f["score"] = _score_relevance(f)

    findings.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Write findings to log
    log_file = f"{log_dir}/scout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump(findings, f, indent=2)

    # Return top finding as actionable insight
    if not findings:
        return {
            "status": "ok",
            "output": "No new findings from horizon scan.",
            "findings": [],
        }

    top = findings[0]
    return {
        "status": "ok",
        "output": (
            f"Scout found: {top['title']} ({top['source']})\n"
            f"Relevance: {top.get('score', 0)}/100\n"
            f"Summary: {top.get('summary', '')[:200]}"
        ),
        "findings": findings[:5],
        "top_finding": top,
    }


def _check_phaser_releases() -> Optional[dict]:
    """Check latest Phaser release via GitHub API."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "8",
             "https://api.github.com/repos/phaserjs/phaser/releases/latest"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        if not data or "tag_name" not in data:
            return None

        tag = data.get("tag_name", "")
        name = data.get("name", "")
        body = (data.get("body") or "")[:500]

        return {
            "title": f"Phaser {tag} released",
            "source": "github:phaserjs/phaser",
            "url": data.get("html_url", ""),
            "summary": name or tag,
            "details": body[:300],
            "type": "engine_update",
            "impact": "high" if "v4." in tag else "medium",
            "score": 90,
        }
    except Exception as e:
        return {
            "title": "Phaser release check failed",
            "source": "github:phaserjs/phaser",
            "url": "",
            "summary": f"Error: {e}",
            "type": "error",
            "impact": "low",
            "score": 0,
        }


def _check_trending() -> list[dict]:
    """Check GitHub trending TypeScript repos."""
    results = []
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10",
             "https://api.github.com/search/repositories?q=phaser+game+engine&sort=stars&order=desc&per_page=5"],
            capture_output=True, text=True, timeout=12,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for item in data.get("items", [])[:3]:
                results.append({
                    "title": item.get("full_name", ""),
                    "source": "github:search",
                    "url": item.get("html_url", ""),
                    "summary": (item.get("description") or "")[:200],
                    "type": "repo",
                    "stars": item.get("stargazers_count", 0),
                    "impact": "medium",
                    "score": min(80, item.get("stargazers_count", 0) // 100),
                })
    except Exception:
        pass
    return results


def _score_relevance(finding: dict) -> int:
    """Score a finding by relevance to our system."""
    score = finding.get("score", 50)
    title = (finding.get("title") or "").lower()
    summary = (finding.get("summary") or "").lower()

    # Boost keywords
    keywords = ["phaser", "render", "shader", "webgl", "particle",
                "game", "animation", "ui", "dashboard", "agent",
                "typescript", "react", "graphics"]
    for kw in keywords:
        if kw in title or kw in summary:
            score += 5

    # Engine updates get priority
    if finding.get("type") == "engine_update":
        score += 15

    return min(100, score)


# ═══════════════════════════════════════════
# RESEARCHER — Deep Diver (3 variants)
# ═══════════════════════════════════════════

async def action_deep_research(config: dict, quest: dict, params: dict) -> dict:
    """Read a URL and synthesize findings into structured knowledge.

    This is the generic researcher. The 'researcher_type' param
    determines variant: 'repo', 'docs', or 'best-practices'.
    """
    url = params.get("url") or quest.get("research_source") or ""
    researcher_type = params.get("researcher_type", "docs")

    if not url:
        return {
            "status": "skipped",
            "output": "No URL provided for research.",
            "simulated": True,
        }

    # Fetch the URL content
    content = _fetch_url(url)
    if not content:
        return {
            "status": "error",
            "output": f"Failed to fetch {url}",
        }

    # Synthesize findings based on researcher type
    synthesis = _synthesize(content, researcher_type)

    log_dir = config.get("log_dir", "/tmp/hermes-logs")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    finding_file = f"{log_dir}/research_{researcher_type}_{timestamp}.md"

    finding_md = _format_finding(url, synthesis, researcher_type)
    with open(finding_file, "w") as f:
        f.write(finding_md)

    # Store in research_findings table via quest engine
    qe = config.get("quest_engine")
    quest_id = quest.get("id", "")
    if qe and quest_id:
        try:
            await qe.db.execute(
                """INSERT INTO research_findings (quest_id, researcher, source_url, summary, impact)
                   VALUES (?, ?, ?, ?, ?)""",
                (quest_id, researcher_type, url, synthesis["summary"], synthesis.get("impact", "medium")),
            )
            await qe.db.commit()
        except Exception as e:
            print(f"[Researcher] DB store error: {e}")

    return {
        "status": "ok",
        "output": f"Researcher ({researcher_type}): synthesized {len(synthesis['key_points'])} key points",
        "filepath": finding_file,
        "synthesis": synthesis,
    }


def _fetch_url(url: str) -> Optional[str]:
    """Fetch a URL's content (text)."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", "10", url],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout[:10000]  # Limit to 10K chars
    except Exception:
        pass
    return None


def _synthesize(content: str, researcher_type: str) -> dict:
    """Synthesize raw content into structured findings.

    In Phase 1, we use heuristic extraction.
    In Phase 2+, we'll delegate to LLM subagent.
    """
    lines = content.split("\n")
    title = ""
    for line in lines[:20]:
        line = line.strip()
        if line.startswith("# ") or line.startswith("## "):
            title = line.lstrip("#").strip()
            break

    key_points = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            key_points.append(stripped[2:].strip()[:200])
        elif stripped.startswith("## "):
            key_points.append(f"[Section] {stripped[3:].strip()}")
        if len(key_points) >= 10:
            break

    impact = "medium"
    if "breaking" in content.lower() or "deprecated" in content.lower():
        impact = "high"
    elif "bug fix" in content.lower() or "minor" in content.lower():
        impact = "low"

    return {
        "title": title or f"{researcher_type} research findings",
        "summary": f"Analyzed {len(lines)} lines as {researcher_type} researcher",
        "key_points": key_points,
        "impact": impact,
        "source_type": researcher_type,
    }


def _format_finding(url: str, synthesis: dict, researcher_type: str) -> str:
    """Format findings as markdown document."""
    lines = [
        f"# Research Finding: {synthesis['title']}",
        f"",
        f"**Type:** {researcher_type} researcher",
        f"**Source:** {url}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Impact:** {synthesis.get('impact', 'medium')}",
        f"",
        f"## Summary",
        f"",
        f"{synthesis['summary']}",
        f"",
        f"## Key Points",
        f"",
    ]
    for i, pt in enumerate(synthesis.get("key_points", []), 1):
        lines.append(f"{i}. {pt}")
    lines.extend([
        "",
        "---",
        f"*Auto-generated by {researcher_type.capitalize()} Researcher (Dungeon OS)*",
    ])
    return "\n".join(lines)


# ═══════════════════════════════════════════
# BRAINMASTER — Knowledge Engineer
# ═══════════════════════════════════════════

async def action_store_knowledge(config: dict, quest: dict, params: dict) -> dict:
    """Store research findings into the Obsidian vault.

    Creates structured notes with frontmatter linking research
    findings to our architecture decisions.
    """
    vault_path = (
        config.get("vault_path")
        or os.getenv("OBSIDIAN_VAULT_PATH")
        or os.path.expanduser("~/Obsidian Vault")
    )

    quest_id = quest.get("id", "unknown")
    title = params.get("title") or quest.get("title", "Research Finding")
    research_summary = params.get("research_summary") or quest.get("goal", "")
    findings = params.get("findings") or []

    # Build frontmatter
    frontmatter = {
        "title": title,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": f"quest:{quest_id}",
        "phase": "head",
        "subsystem": quest.get("subsystem", "knowledge"),
        "tags": ["agora-research", "head", quest.get("subsystem", "knowledge")],
        "status": "draft",
    }

    content_parts = [
        "---",
        json.dumps(frontmatter, indent=2),
        "---",
        "",
        f"# {title}",
        "",
        f"*Generated by Brainmaster (Dungeon OS) on {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Research Summary",
        "",
        research_summary,
        "",
    ]

    if findings:
        content_parts.extend([
            "## Key Findings",
            "",
        ])
        for f in findings:
            if isinstance(f, dict):
                content_parts.append(f"- **{f.get('researcher', 'unknown')}:** {f.get('summary', '')[:300]}")
            else:
                content_parts.append(f"- {f}")

    content_parts.extend([
        "",
        "## Quest Context",
        "",
        f"- **Quest ID:** {quest_id}",
        f"- **Subsystem:** {quest.get('subsystem', 'knowledge')}",
        f"- **Phase:** head",
        "",
        "---",
        "",
        "*Auto-generated by Brainmaster as part of the Autonomous Agent Corporation*",
    ])

    content = "\n".join(content_parts)

    # Write to vault — agora-research/
    vault = Path(vault_path)
    research_dir = vault / "agora-research"
    research_dir.mkdir(parents=True, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:60]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M')}_{safe_title}.md"
    filepath = research_dir / filename

    filepath.write_text(content)

    # Also write to agora-proposals/ for vetted proposals
    proposals_dir = vault / "agora-proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)

    # Update quest with findings path
    qe = config.get("quest_engine")
    if qe and quest_id:
        try:
            await qe.db.execute(
                "UPDATE quests SET findings_path=?, research_summary=? WHERE id=?",
                (str(filepath), research_summary[:500], quest_id),
            )
            await qe.db.commit()
        except Exception as e:
            print(f"[Brainmaster] DB update error: {e}")

    return {
        "status": "ok",
        "output": f"Knowledge stored to {filepath} ({len(content)} bytes)",
        "filepath": str(filepath),
    }


# ═══════════════════════════════════════════
# CEO/CTO — Proposal Evaluation + Adversarial
# ═══════════════════════════════════════════

async def action_evaluate_proposal(config: dict, quest: dict, params: dict) -> dict:
    """CEO/CTO evaluate a research proposal.

    Adversarial filtering: the CTO critiques technical merit,
    CEO evaluates business value. Only if both approve → PATA phase.
    """
    quest_id = quest.get("id", "")
    title = quest.get("title", "")
    research_summary = quest.get("research_summary") or quest.get("goal", "")
    subsystem = quest.get("subsystem", "knowledge")

    # CTO evaluation (technical)
    cto_verdict = await _cto_evaluate_llm(title, research_summary, subsystem)
    # CEO evaluation (strategic)
    ceo_verdict = await _ceo_evaluate_llm(title, research_summary)

    approved = cto_verdict.get("approved", False) and ceo_verdict.get("approved", False)
    priority = "HIGH" if approved and cto_verdict["priority"] == "high" else "MEDIUM"

    # If approved, advance quest to PATA phase
    qe = config.get("quest_engine")
    if qe and quest_id and approved:
        try:
            await qe.db.execute(
                """UPDATE quests SET phase='pata', proposal_status='approved',
                   research_summary=? WHERE id=?""",
                (f"CTO: {cto_verdict['rationale'][:200]}\nCEO: {ceo_verdict['rationale'][:200]}",
                 quest_id),
            )
            await qe.db.commit()
        except Exception as e:
            print(f"[CEO/CTO] DB update error: {e}")

    return {
        "status": "ok" if approved else "rejected",
        "output": (
            f"CEO/CTO Evaluation for '{quest_id}': {'✅ APPROVED' if approved else '❌ REJECTED'}\n"
            f"Priority: {priority}\n"
            f"CTO: {cto_verdict['rationale']}\n"
            f"CEO: {ceo_verdict['rationale']}\n"
            f"{'→ Moving to PATA phase' if approved else '→ Research needs improvement'}"
        ),
        "approved": approved,
        "priority": priority,
        "cto": cto_verdict,
        "ceo": ceo_verdict,
    }


async def _cto_evaluate_llm(title: str, summary: str, subsystem: str) -> dict:
    """CTO evaluates technical merit using LLM."""
    from agora.execution.llm_client import call_llm

    prompt = get_role_prompt("cto")
    user_msg = (
        f"## Research Proposal: {title}\n\n"
        f"### Technical Summary\n{summary[:1000]}\n\n"
        f"### Current Subsystem\n{subsystem}\n\n"
        f"### Evaluation Required\n"
        f"Assess this proposal on:\n"
        f"1. Technical merit (is this sound?)\n"
        f"2. Architecture impact (does it improve or complicate our system?)\n"
        f"3. Integration complexity (how hard to implement?)\n"
        f"4. Performance implications (faster, slower?)\n\n"
        f"Respond with JSON:\n"
        f'{{"approved": true/false, "rationale": "reason", "priority": "high/medium/low", "score": 0-100}}'
    )

    try:
        # Run sync LLM call in thread to avoid blocking event loop
        import asyncio
        raw = await asyncio.to_thread(
            call_llm,
            system_prompt=prompt,
            user_prompt=user_msg,
            tier="cheap",
            temperature=0.3,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(raw)
        return {
            "approved": parsed.get("approved", False),
            "rationale": parsed.get("rationale", "LLM evaluation unavailable"),
            "priority": parsed.get("priority", "medium"),
            "score": parsed.get("score", 50),
        }
    except Exception as e:
        import traceback
        print(f"[CTO] LLM eval failed: {e}\n{traceback.format_exc()[:200]}")
        # Fallback to heuristic
        combined = (title + " " + summary).lower()
        score = 50
        for kw in ["performance", "render", "webgl", "optimization", "new feature", "upgrade"]:
            if kw in combined:
                score += 10
        return {
            "approved": score >= 60,
            "rationale": f"Heuristic fallback (LLM failed): technical score {score}/100",
            "priority": "high" if score >= 75 else "medium",
            "score": score,
        }


async def _ceo_evaluate_llm(title: str, summary: str) -> dict:
    """CEO evaluates strategic/business value using LLM."""
    from agora.execution.llm_client import call_llm

    prompt = get_role_prompt("ceo")
    user_msg = (
        f"Proposal: {title}\n\n"
        f"Summary: {summary[:600]}\n\n"
        f"Assess strategic value, user impact, and opportunity cost. "
        f"Respond with JSON:\n"
        f'{{"approved": true/false, "rationale": "reason", "score": 0-100}}'
    )

    try:
        import asyncio
        raw = await asyncio.to_thread(
            call_llm,
            system_prompt=prompt,
            user_prompt=user_msg,
            tier="cheap",
            temperature=0.3,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(raw)
        return {
            "approved": parsed.get("approved", False),
            "rationale": parsed.get("rationale", "LLM evaluation unavailable"),
            "score": parsed.get("score", 50),
        }
    except Exception as e:
        import traceback
        print(f"[CEO] LLM eval failed: {e}\n{traceback.format_exc()[:200]}")
        # Fallback to heuristic
        combined = (title + " " + summary).lower()
        score = 50
        for kw in ["player", "user", "experience", "graphics", "new feature", "community", "ui"]:
            if kw in combined:
                score += 10
        return {
            "approved": score >= 60,
            "rationale": f"Heuristic fallback (LLM failed): strategic score {score}/100",
            "score": score,
        }


# ═══════════════════════════════════════════
# COMPOUND — Lessons Learned
# ═══════════════════════════════════════════

async def action_compound(config: dict, quest: dict, params: dict) -> dict:
    """Extract lessons from a completed quest cycle.

    Writes to AGENTS.md / MEMORY.md for permanent improvement.
    This is the recursive self-improvement step.
    """
    quest_id = quest.get("id", "")
    title = quest.get("title", "")
    status = quest.get("status", "")
    research_summary = quest.get("research_summary", "")
    phase = quest.get("phase", "")

    lessons = []

    if status == "done" and phase == "pata":
        lessons.append(f"✅ Completed quest '{title}' through full HEAD→PATA cycle")
        lessons.append(f"   Research summary: {research_summary[:200]}")
    elif status == "done" and phase == "head":
        lessons.append(f"📚 Completed HEAD research for '{title}'")
        lessons.append(f"   Knowledge stored in vault")
    else:
        lessons.append(f"⏭️  Quest '{title}' ({phase}/{status}) — no compound lessons extracted")

    # Write to compound log
    log_dir = config.get("log_dir", "/tmp/hermes-logs")
    os.makedirs(log_dir, exist_ok=True)
    compound_file = f"{log_dir}/compound_{quest_id}.md"
    with open(compound_file, "w") as f:
        f.write("\n".join([
            f"# Compound: {title}",
            f"",
            f"**Quest:** {quest_id}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Final phase:** {phase}",
            f"**Final status:** {status}",
            f"",
            "## Lessons Learned",
            "",
        ] + [f"- {l}" for l in lessons] + [
            "",
            "---",
            "*Auto-generated by Compound step (Dungeon OS)*",
        ]))

    # Store compound lessons in DB
    qe = config.get("quest_engine")
    if qe and quest_id:
        try:
            await qe.db.execute(
                "UPDATE quests SET compound_lessons=? WHERE id=?",
                ("\n".join(lessons), quest_id),
            )
            await qe.db.commit()
        except Exception as e:
            print(f"[Compound] DB update error: {e}")

    return {
        "status": "ok",
        "output": f"Compound: extracted {len(lessons)} lessons from '{quest_id}'",
        "lessons": lessons,
        "compound_file": compound_file,
    }
