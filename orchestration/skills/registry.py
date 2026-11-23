"""Registry load/save, lifecycle transitions, rollback and derived permissions.

The registry is the factory's single source of truth (architecture D-2).
``opencode.json`` skill rules are a *derived artifact* (D-4 / I-3): this module
renders them deterministically so CI can regenerate-and-diff instead of
trusting hand edits.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union

from .models import (
    ALLOWED_TRANSITIONS,
    DEFAULT_RULE_BY_RISK,
    EVENT_BY_LIFECYCLE,
    RULE_STRICTNESS,
    HistoryEntry,
    Lifecycle,
    Rule,
    SkillEntry,
    _plain,
)


class RegistryError(ValueError):
    """Raised for illegal registry mutations (duplicate IDs, bad transitions)."""


class Registry:
    """In-memory registry envelope with append-only per-row history."""

    def __init__(
        self,
        schema_version: str = "1.0",
        registry_version: str = "0.1.0",
        updated_at: str = "TBD",
        skills: Optional[Iterable[SkillEntry]] = None,
    ) -> None:
        self.schema_version = schema_version
        self.registry_version = registry_version
        self.updated_at = updated_at
        self._entries: Dict[str, SkillEntry] = {}
        for entry in skills or []:
            self.add(entry)

    # -- construction -------------------------------------------------------
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Registry":
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            registry_version=data.get("registry_version", "0.1.0"),
            updated_at=data.get("updated_at", "TBD"),
            skills=[SkillEntry.from_dict(row) for row in data.get("skills", [])],
        )

    @classmethod
    def load(cls, path: Union[str, Path]) -> "Registry":
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_dict(json.loads(text))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "registry_version": self.registry_version,
            "updated_at": self.updated_at,
            "skills": [entry.to_dict() for entry in self._entries.values()],
        }

    def save(self, path: Union[str, Path]) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = date.today().isoformat()
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    # -- accessors ----------------------------------------------------------
    def add(self, entry: SkillEntry) -> SkillEntry:
        if entry.skill_id in self._entries:
            raise RegistryError("duplicate skill_id: %s (rows are never duplicated)" % entry.skill_id)
        self._entries[entry.skill_id] = entry
        return entry

    def get(self, skill_id: str) -> Optional[SkillEntry]:
        return self._entries.get(skill_id)

    def require(self, skill_id: str) -> SkillEntry:
        entry = self.get(skill_id)
        if entry is None:
            raise RegistryError("unknown skill_id: %s" % skill_id)
        return entry

    def skill_ids(self) -> List[str]:
        return list(self._entries.keys())

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[SkillEntry]:
        return iter(self._entries.values())

    # -- lifecycle ----------------------------------------------------------
    def transition(
        self,
        skill_id: str,
        target: Union[str, Lifecycle],
        *,
        gates: Optional[List[str]] = None,
        adr: Optional[str] = None,
        actor: Optional[str] = None,
        evidence: Optional[str] = None,
        date_str: Optional[str] = None,
    ) -> SkillEntry:
        """Apply a guarded lifecycle transition and append one history entry.

        Illegal transitions raise :class:`RegistryError` and leave the row
        untouched (fail-closed: no partial mutation).
        """
        entry = self.require(skill_id)
        target = target if isinstance(target, Lifecycle) else Lifecycle(target)
        current = entry.lifecycle
        if target not in ALLOWED_TRANSITIONS[current]:
            raise RegistryError(
                "illegal lifecycle transition %s -> %s for %s" % (current.value, target.value, skill_id)
            )

        # Permission/enablement posture per §4.2 of the schema specification.
        if target in (Lifecycle.CANDIDATE, Lifecycle.REVIEWED, Lifecycle.APPROVED, Lifecycle.RETIRED):
            entry.enabled_in = []
            entry.permissions.rule = Rule.DENY
        elif target == Lifecycle.STAGED:
            if not entry.enabled_in:
                entry.enabled_in = [".opencode/skills/%s" % entry.skill_id]
            entry.permissions.rule = Rule.ASK
            entry.permissions.per_agent_overrides = {}
        elif target == Lifecycle.ACTIVE:
            if not entry.enabled_in:
                entry.enabled_in = [".opencode/skills/%s" % entry.skill_id]
            entry.permissions.rule = DEFAULT_RULE_BY_RISK[entry.permissions.risk_class.value]
        elif target == Lifecycle.SUSPENDED:
            # Kill-switch: copies may remain on disk but every rule is deny and
            # no override may relax it (P-2).
            entry.permissions.rule = Rule.DENY
            entry.permissions.per_agent_overrides = {}

        entry.lifecycle = target
        entry.versioning.history.append(
            self._history_entry(EVENT_BY_LIFECYCLE[target], date_str, gates, adr, actor, evidence)
        )
        self.updated_at = date_str or date.today().isoformat()
        return entry

    def rollback(
        self,
        skill_id: str,
        *,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        date_str: Optional[str] = None,
    ) -> SkillEntry:
        """Per-skill rollback: kill-switch, artifact removal, row retained (T-3).

        1. deny everywhere (permission kill-switch);
        2. remove the artifact from all enablement sources (`enabled_in: []`);
        3. V-3 must be re-run by the caller to catch silent resurrection;
        4. the row is kept with an append-only SUSPENDED history entry.
        """
        entry = self.require(skill_id)
        if entry.lifecycle == Lifecycle.RETIRED:
            raise RegistryError("cannot roll back RETIRED row: %s" % skill_id)

        entry.permissions.rule = Rule.DENY
        entry.permissions.per_agent_overrides = {}
        entry.enabled_in = []
        previous = entry.lifecycle
        entry.lifecycle = Lifecycle.SUSPENDED
        evidence_parts = ["rollback from %s" % previous.value]
        if reason:
            evidence_parts.append("reason: %s" % reason)
        entry.versioning.history.append(
            self._history_entry(
                EVENT_BY_LIFECYCLE[Lifecycle.SUSPENDED],
                date_str,
                None,
                None,
                actor,
                "; ".join(evidence_parts),
            )
        )
        self.updated_at = date_str or date.today().isoformat()
        return entry

    @staticmethod
    def _history_entry(
        event: Any,
        date_str: Optional[str],
        gates: Optional[List[str]],
        adr: Optional[str],
        actor: Optional[str],
        evidence: Optional[str],
    ) -> HistoryEntry:
        return HistoryEntry(
            event=event,
            date=date_str or date.today().isoformat(),
            gates=list(gates or []),
            adr=adr,
            actor=actor,
            evidence=evidence,
        )

    # -- derived permissions -------------------------------------------------
    @staticmethod
    def effective_rule(entry: SkillEntry, agent_id: str) -> Rule:
        """Resolve the effective skill rule for one agent (fail-closed)."""
        if entry.lifecycle == Lifecycle.SUSPENDED:
            return Rule.DENY
        if entry.lifecycle == Lifecycle.STAGED:
            return Rule.ASK
        default = DEFAULT_RULE_BY_RISK[entry.permissions.risk_class.value]
        override = entry.permissions.per_agent_overrides.get(agent_id)
        # Overrides may tighten freely; loosening needs human-approved history
        # evidence (X-8) and is therefore *not* applied by the generator.
        if override is not None and RULE_STRICTNESS[override] >= RULE_STRICTNESS[default]:
            return override
        return default

    def derive_permissions(self) -> Dict[str, Any]:
        """Render the derived ``opencode.json`` skill-permission document."""
        agents: Dict[str, List[Dict[str, str]]] = {}
        for entry in self._entries.values():
            if entry.lifecycle not in (Lifecycle.STAGED, Lifecycle.ACTIVE, Lifecycle.SUSPENDED):
                continue
            # A SUSPENDED row keeps an explicit deny rule even after its
            # artifact was removed: the kill-switch must survive rollback and
            # guard against silent resurrection (GOV-2 / T-3).
            if not entry.enabled_in and entry.lifecycle != Lifecycle.SUSPENDED:
                continue
            for agent_id in entry.assignment.agents:
                rule = self.effective_rule(entry, agent_id)
                agents.setdefault(agent_id, []).append(
                    {"action": rule.value, "pattern": entry.skill_id}
                )

        rendered_agents: Dict[str, Any] = {}
        for agent_id in sorted(agents):
            # Ordered rules, last match wins: deny is sorted last so the
            # kill-switch always wins regardless of insertion order.
            rules = sorted(agents[agent_id], key=lambda r: (r["action"] == Rule.DENY.value, r["pattern"]))
            rendered_agents[agent_id] = {"permissions": {"skill": rules}}

        return _plain(
            {
                "$schema": "https://opencode.ai/config.json",
                "permissions": {"skill": Rule.DENY.value},
                "agents": rendered_agents,
            }
        )


def render_permissions(registry: Union[Registry, Dict[str, Any]]) -> str:
    """Canonical byte-for-byte rendering of the derived config (I-3)."""
    if isinstance(registry, dict):
        registry = Registry.from_dict(registry)
    return json.dumps(registry.derive_permissions(), indent=2, sort_keys=True) + "\n"


__all__ = ["Registry", "RegistryError", "render_permissions"]
