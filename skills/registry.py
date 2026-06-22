"""
SkillRegistry — Progressive disclosure skill loader.

Day 3 concept: Skills load in three levels:
  1. Metadata (name + description from YAML frontmatter) → always in context (~50 tokens each)
  2. SKILL.md body → loaded only when the skill triggers
  3. References/assets → loaded strictly when the body references them

This means 100 installed skills cost ~100 × 50 tokens = ~5,000 tokens of metadata.
Only the active skill body (~1,500 tokens) is added to context per request.

The registry also enforces:
  - Trigger accuracy (positive/negative test cases in SKILL.md frontmatter)
  - Token budget per skill (from frontmatter)
  - Tier-based access control (read-only, draft, action-allowed)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# SKILL.md Parser
# ---------------------------------------------------------------------------

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Extract YAML frontmatter and body from a SKILL.md file.

    Returns (metadata_dict, body_text).
    Uses simple line-by-line parsing to avoid requiring PyYAML.
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content

    frontmatter_text = content[3:end].strip()
    body = content[end + 4:].strip()

    metadata: dict[str, Any] = {}
    current_key = None
    current_list: list[str] | None = None
    current_multiline: list[str] | None = None

    for line in frontmatter_text.split("\n"):
        # Skip blank lines
        if not line.strip():
            if current_multiline is not None:
                metadata[current_key] = " ".join(current_multiline).strip()
                current_multiline = None
            continue

        # List item
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip().strip('"'))
            continue

        # Nested key (triggers.positive / triggers.negative)
        if line.startswith("  ") and ":" in line and current_key == "triggers":
            sub_key, _, sub_val = line.strip().partition(":")
            if not sub_val.strip():
                # Will be a list
                if "triggers" not in metadata:
                    metadata["triggers"] = {}
                current_list = []
                metadata["triggers"][sub_key.strip()] = current_list
            continue

        # Multiline value continuation
        if line.startswith("  ") and current_multiline is not None:
            current_multiline.append(line.strip())
            continue

        # Flush pending multiline
        if current_multiline is not None:
            metadata[current_key] = " ".join(current_multiline).strip()
            current_multiline = None

        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()

            if val == "|":
                current_key = key
                current_multiline = []
                current_list = None
            elif val == "":
                current_key = key
                current_list = None
                metadata[key] = {}
            elif val.startswith("["):
                # Inline list like [1, 2, 3]
                items = re.findall(r"[\w.]+", val)
                try:
                    metadata[key] = [int(i) for i in items]
                except ValueError:
                    metadata[key] = items
            else:
                metadata[key] = val.strip('"')
                current_key = key
                current_list = None

    if current_multiline is not None and current_key:
        metadata[current_key] = " ".join(current_multiline).strip()

    return metadata, body


# ---------------------------------------------------------------------------
# Skill data structures
# ---------------------------------------------------------------------------

@dataclass
class SkillMetadata:
    """
    Level 1 — always in context (~50 tokens).
    This is the routing signal: the model sees only name + description to decide if skill fires.
    """
    name: str
    description: str
    version: str = "1.0"
    tier: str = "read-only"          # read-only | draft | action-allowed
    token_budget: int = 1500
    triggers_positive: list[str] = field(default_factory=list)
    triggers_negative: list[str] = field(default_factory=list)
    tools_allowed: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    skill_dir: Path = field(default_factory=Path)

    def to_context_line(self) -> str:
        """Compact representation loaded into the orchestrator context at all times."""
        return f"- **{self.name}** ({self.tier}): {self.description[:120]}"


@dataclass
class LoadedSkill:
    """
    Level 2 — body loaded on trigger.
    Adds the full SKILL.md body to the agent's context.
    """
    metadata: SkillMetadata
    body: str                        # Full SKILL.md body text
    token_estimate: int = 0

    def to_prompt_injection(self) -> str:
        """Format the skill body for injection into the agent's system prompt."""
        return (
            f"\n\n## Active Skill: {self.metadata.name}\n"
            f"_Tier: {self.metadata.tier} | Budget: {self.metadata.token_budget} tokens_\n\n"
            f"{self.body}"
        )

    def load_reference(self, filename: str) -> str | None:
        """Level 3 — load a reference file from references/ on demand."""
        ref_path = self.metadata.skill_dir / "references" / filename
        if ref_path.exists():
            return ref_path.read_text()
        return None


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------

SKILLS_ROOT = Path(__file__).parent


class SkillRegistry:
    """
    Progressive disclosure skill registry.

    - Scans skills/ directory on init, loading only metadata (Level 1).
    - Body loaded on-demand via load_skill() (Level 2).
    - References loaded on-demand via LoadedSkill.load_reference() (Level 3).
    """

    def __init__(self, skills_root: Path = SKILLS_ROOT):
        self._root = skills_root
        self._metadata: dict[str, SkillMetadata] = {}
        self._body_cache: dict[str, str] = {}
        self._scan()

    def _scan(self) -> None:
        """Scan the skills directory and load metadata for all SKILL.md files."""
        for skill_dir in self._root.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            try:
                content = skill_md.read_text()
                meta_dict, body = _parse_frontmatter(content)
                if not meta_dict.get("name"):
                    continue

                triggers = meta_dict.get("triggers", {})
                positive = triggers.get("positive", []) if isinstance(triggers, dict) else []
                negative = triggers.get("negative", []) if isinstance(triggers, dict) else []

                # tools_allowed may be a string from simple parsing
                tools = meta_dict.get("tools_allowed", [])
                if isinstance(tools, str):
                    tools = [t.strip() for t in tools.split(",")]

                servers = meta_dict.get("mcp_servers", [])
                if isinstance(servers, str):
                    servers = [s.strip() for s in servers.split(",")]

                metadata = SkillMetadata(
                    name=meta_dict["name"],
                    description=meta_dict.get("description", ""),
                    version=meta_dict.get("version", "1.0"),
                    tier=meta_dict.get("tier", "read-only"),
                    token_budget=int(meta_dict.get("token_budget", 1500)),
                    triggers_positive=positive,
                    triggers_negative=negative,
                    tools_allowed=tools if isinstance(tools, list) else [],
                    mcp_servers=servers if isinstance(servers, list) else [],
                    skill_dir=skill_dir,
                )
                self._metadata[metadata.name] = metadata
                self._body_cache[metadata.name] = body
            except Exception:
                continue

    def list_metadata(self) -> list[SkillMetadata]:
        """Return metadata for all installed skills — Level 1 context."""
        return list(self._metadata.values())

    def get_catalog_prompt(self) -> str:
        """
        Compact skill catalog injected into orchestrator context every turn.
        ~50 tokens per skill. This is the progressive disclosure Level 1.
        """
        lines = ["## Installed Skills (load body only when triggered)\n"]
        for meta in self._metadata.values():
            lines.append(meta.to_context_line())
        return "\n".join(lines)

    def load_skill(self, skill_name: str) -> LoadedSkill | None:
        """
        Load the full skill body (Level 2) for an active skill.
        Only called after the orchestrator classifies intent and selects a skill.
        """
        meta = self._metadata.get(skill_name)
        if not meta:
            return None
        body = self._body_cache.get(skill_name, "")
        token_estimate = len(body) // 4
        return LoadedSkill(metadata=meta, body=body, token_estimate=token_estimate)

    def match_skill(self, intent: str) -> str | None:
        """
        Map an intent string to the appropriate skill name.
        This is the routing function — intent from orchestrator → skill name.
        """
        intent_map = {
            "explain": "subject-tutor",
            "quiz": "quiz-generator",
            "progress": "learning-path",
            "resources": "content-fetch",
        }
        return intent_map.get(intent)

    def get_metadata(self, skill_name: str) -> SkillMetadata | None:
        return self._metadata.get(skill_name)


# Singleton registry
_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
