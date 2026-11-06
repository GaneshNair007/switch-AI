"""Data schemas and types for Antigravity Agent Scope Guard.

Defines the contracts for Assignments, Policy Decisions, Violations,
Approval Requests, and Actions.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class DecisionCategory(str, Enum):
    """Action decision categories per build specification."""
    ALLOW = "ALLOW"
    WARN = "WARN"
    ASK = "ASK"
    BLOCK = "BLOCK"


class ViolationCategory(str, Enum):
    """Categories of scope and ownership violations."""
    OUT_OF_SCOPE_MODIFICATION = "OUT_OF_SCOPE_MODIFICATION"
    RESTRICTED_PATH_ACCESS = "RESTRICTED_PATH_ACCESS"
    OWNERSHIP_COLLISION = "OWNERSHIP_COLLISION"
    PATH_TRAVERSAL_ATTEMPT = "PATH_TRAVERSAL_ATTEMPT"
    DESTRUCTIVE_COMMAND = "DESTRUCTIVE_COMMAND"
    UNAUTHORIZED_SCOPE_EXPANSION = "UNAUTHORIZED_SCOPE_EXPANSION"
    STALE_ASSIGNMENT = "STALE_ASSIGNMENT"
    UNSUPPORTED_INTERCEPTION = "UNSUPPORTED_INTERCEPTION"


class SeverityLevel(str, Enum):
    """Violation severity levels."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskStatus(str, Enum):
    """Coordinator task status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApprovalStatus(str, Enum):
    """Scope expansion approval status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class OwnershipRecord:
    """Ownership assignment for a file pattern belonging to another agent."""
    path_pattern: str
    owner_agent_id: str
    description: Optional[str] = None
    reservation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OwnershipRecord:
        return cls(
            path_pattern=data["path_pattern"],
            owner_agent_id=data["owner_agent_id"],
            description=data.get("description"),
            reservation_id=data.get("reservation_id"),
        )


@dataclass
class Assignment:
    """The formal task assignment and scope policy contract from coordinator."""
    agent_id: str
    task_id: str
    task_description: str
    allowed_paths: List[str]
    restricted_paths: List[str] = field(default_factory=list)
    ownership_info: List[OwnershipRecord] = field(default_factory=list)
    task_status: TaskStatus = TaskStatus.IN_PROGRESS
    assignment_version: int = 1
    exceptions: List[str] = field(default_factory=list)
    prohibited_operations: List[str] = field(default_factory=list)
    require_approval_for_unowned: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["task_status"] = self.task_status.value
        data["ownership_info"] = [o.to_dict() for o in self.ownership_info]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Assignment:
        ownership = [
            OwnershipRecord.from_dict(item) if isinstance(item, dict) else item
            for item in data.get("ownership_info", [])
        ]
        status_val = data.get("task_status", TaskStatus.IN_PROGRESS.value)
        status = TaskStatus(status_val) if isinstance(status_val, str) else status_val
        return cls(
            agent_id=data["agent_id"],
            task_id=data["task_id"],
            task_description=data.get("task_description", ""),
            allowed_paths=list(data.get("allowed_paths", [])),
            restricted_paths=list(data.get("restricted_paths", [])),
            ownership_info=ownership,
            task_status=status,
            assignment_version=int(data.get("assignment_version", 1)),
            exceptions=list(data.get("exceptions", [])),
            prohibited_operations=list(data.get("prohibited_operations", [])),
            require_approval_for_unowned=bool(data.get("require_approval_for_unowned", False)),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            expires_at=data.get("expires_at"),
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> Assignment:
        return cls.from_dict(json.loads(json_str))


@dataclass
class ActionRequest:
    """An intercepted agent tool action attempting modification or execution."""
    tool_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
    step_idx: Optional[int] = None
    conversation_id: Optional[str] = None
    target_path: Optional[str] = None
    raw_command: Optional[str] = None
    workspace_root: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyDecision:
    """The explainable evaluation result for an attempted action."""
    decision: DecisionCategory
    reason: str
    explanation: str
    category: Optional[ViolationCategory] = None
    severity: SeverityLevel = SeverityLevel.INFO
    owner: Optional[str] = None
    target_path: Optional[str] = None
    agent_id: Optional[str] = None
    assignment_version: Optional[int] = None

    @property
    def is_blocked(self) -> bool:
        return self.decision in (DecisionCategory.BLOCK, DecisionCategory.ASK)

    @property
    def is_allowed(self) -> bool:
        return self.decision in (DecisionCategory.ALLOW, DecisionCategory.WARN)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "explanation": self.explanation,
            "category": self.category.value if self.category else None,
            "severity": self.severity.value,
            "owner": self.owner,
            "target_path": self.target_path,
            "agent_id": self.agent_id,
            "assignment_version": self.assignment_version,
            "is_blocked": self.is_blocked,
        }


@dataclass
class ViolationEvent:
    """Structured violation report transmitted to coordinator and logged locally."""
    event_id: str
    agent_id: str
    task_id: str
    timestamp: str
    attempted_tool: str
    target_path: Optional[str]
    violation_category: ViolationCategory
    severity: SeverityLevel
    decision_taken: DecisionCategory
    explanation: str
    assignment_version: int
    raw_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "attempted_tool": self.attempted_tool,
            "target_path": self.target_path,
            "violation_category": self.violation_category.value,
            "severity": self.severity.value,
            "decision_taken": self.decision_taken.value,
            "explanation": self.explanation,
            "assignment_version": self.assignment_version,
            "raw_details": self.raw_details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ViolationEvent:
        return cls(
            event_id=data["event_id"],
            agent_id=data["agent_id"],
            task_id=data["task_id"],
            timestamp=data["timestamp"],
            attempted_tool=data["attempted_tool"],
            target_path=data.get("target_path"),
            violation_category=ViolationCategory(data["violation_category"]),
            severity=SeverityLevel(data["severity"]),
            decision_taken=DecisionCategory(data["decision_taken"]),
            explanation=data["explanation"],
            assignment_version=int(data.get("assignment_version", 1)),
            raw_details=dict(data.get("raw_details", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class ApprovalRequest:
    """Request created when out-of-scope modification requires coordinator approval."""
    request_id: str
    agent_id: str
    task_id: str
    attempted_action: str
    target_path: str
    reason: str
    current_version: int
    requested_paths: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: ApprovalStatus = ApprovalStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApprovalRequest:
        status_val = data.get("status", ApprovalStatus.PENDING.value)
        status = ApprovalStatus(status_val) if isinstance(status_val, str) else status_val
        return cls(
            request_id=data["request_id"],
            agent_id=data["agent_id"],
            task_id=data["task_id"],
            attempted_action=data["attempted_action"],
            target_path=data["target_path"],
            reason=data["reason"],
            current_version=int(data.get("current_version", 1)),
            requested_paths=list(data.get("requested_paths", [])),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            status=status,
        )


@dataclass
class ApprovalResponse:
    """Response received from coordinator regarding an approval request."""
    request_id: str
    status: ApprovalStatus
    approved_by: Optional[str] = None
    updated_assignment: Optional[Assignment] = None
    reason: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "approved_by": self.approved_by,
            "updated_assignment": self.updated_assignment.to_dict() if self.updated_assignment else None,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApprovalResponse:
        status_val = data.get("status", ApprovalStatus.PENDING.value)
        status = ApprovalStatus(status_val) if isinstance(status_val, str) else status_val
        updated = None
        if data.get("updated_assignment"):
            updated = Assignment.from_dict(data["updated_assignment"])
        return cls(
            request_id=data["request_id"],
            status=status,
            approved_by=data.get("approved_by"),
            updated_assignment=updated,
            reason=data.get("reason"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )
