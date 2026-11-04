"""Tamper-Evident Cryptographic Audit Ledger for Ship Court.

Chains every motion, objection, concession, and human judicial decree into an
append-only SHA-256 hash sequence to ensure non-repudiation and SOX/SOC2 audit compliance.
"""
from __future__ import annotations
import hashlib
import json
import time
from typing import List, Dict, Any, Optional

class AuditEntry:
    def __init__(self, index: int, event_type: str, actor: str, payload: Dict[str, Any], prev_hash: str):
        self.index = index
        self.timestamp = time.time()
        self.event_type = event_type
        self.actor = actor
        self.payload = payload
        self.prev_hash = prev_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "payload": self.payload,
            "prev_hash": self.prev_hash
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash
        }

class AuditLedger:
    """Cryptographic hash chain verifying courtroom decision lineage."""

    def __init__(self, case_id: str):
        self.case_id = case_id
        self.chain: List[AuditEntry] = []
        self._initialize_genesis_block()

    def _initialize_genesis_block(self) -> None:
        genesis = AuditEntry(
            index=0,
            event_type="CASE_GENESIS",
            actor="system",
            payload={"case_id": self.case_id, "protocol": "ShipCourt-v1.0"},
            prev_hash="0" * 64
        )
        self.chain.append(genesis)

    @property
    def latest_entry(self) -> AuditEntry:
        return self.chain[-1]

    def append_event(self, event_type: str, actor: str, payload: Dict[str, Any]) -> AuditEntry:
        """Append a new evidentiary event or judicial decree to the ledger."""
        new_entry = AuditEntry(
            index=len(self.chain),
            event_type=event_type,
            actor=actor,
            payload=payload,
            prev_hash=self.latest_entry.hash
        )
        self.chain.append(new_entry)
        return new_entry

    def verify_integrity(self) -> bool:
        """Validate every block's internal hash and parent link."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Re-calculate hash
            if current.hash != current.calculate_hash():
                return False
            # Check link to previous hash
            if current.prev_hash != previous.hash:
                return False
        return True

    def export_audit_manifest(self) -> Dict[str, Any]:
        """Generate compliance-ready JSON audit manifest."""
        return {
            "case_id": self.case_id,
            "total_events": len(self.chain),
            "root_genesis_hash": self.chain[0].hash,
            "final_seal_hash": self.latest_entry.hash,
            "is_valid": self.verify_integrity(),
            "events": [e.to_dict() for e in self.chain]
        }
