"""Ship Court Data Models and Contracts as specified in Section 10.4 of Blueprint."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

class CaseState(str, Enum):
    CASE_OPENED = "CASE_OPENED"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    OBJECTIONS_RAISED = "OBJECTIONS_RAISED"
    DEFENSE_RESPONSE = "DEFENSE_RESPONSE"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"
    AWAITING_VERDICT = "AWAITING_VERDICT"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    CONDITIONAL = "CONDITIONAL"
    CASE_CLOSED = "CASE_CLOSED"

class ObjectionSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    NOTE = "NOTE"

class ObjectionStatus(str, Enum):
    OPEN = "OPEN"
    MITIGATED = "MITIGATED"
    CONCEDED = "CONCEDED"
    RESOLVED = "RESOLVED"

class RollbackStatus(str, Enum):
    READY = "READY"
    MISSING_OWNER = "MISSING_OWNER"
    UNTESTED = "UNTESTED"
    BLOCKED = "BLOCKED"

class VerdictType(str, Enum):
    APPROVE = "APPROVE"
    BLOCK = "BLOCK"
    CONDITIONS = "CONDITIONS"

@dataclass
class Objection:
    id: str
    claim: str
    evidence: str
    classification: ObjectionSeverity
    status: ObjectionStatus = ObjectionStatus.OPEN

@dataclass
class Defense:
    objection_id: str
    claim: str
    evidence: str
    is_conceded: bool = False

@dataclass
class RollbackPlan:
    current_version: str
    target_version: str
    command: str
    health_checks: List[str]
    rollback_owner: str
    execution_status: RollbackStatus = RollbackStatus.READY

@dataclass
class Condition:
    id: str
    description: str
    owner: str

@dataclass
class Verdict:
    judge: str
    type: VerdictType
    reason: Optional[str] = None
    conditions: List[Condition] = field(default_factory=list)

@dataclass
class Task:
    id: str
    description: str
    owner: str
    status: str = "OPEN"

@dataclass
class Case:
    case_id: str
    pr_url: str
    repository: str
    affected_services: List[str]
    ci_status: str
    deployment_target: str
    state: CaseState = CaseState.CASE_OPENED
    objections: List[Objection] = field(default_factory=list)
    defenses: List[Defense] = field(default_factory=list)
    rollback_plan: Optional[RollbackPlan] = None
    verdict: Optional[Verdict] = None
    tasks: List[Task] = field(default_factory=list)
    release_brief: str = ""
    round_count: int = 0
