"""Tests for AuditLedger cryptographic hash chain integrity and tamper detection."""
import pytest
from server.audit_ledger import AuditLedger

def test_ledger_initialization():
    ledger = AuditLedger("SC-TEST-001")
    assert len(ledger.chain) == 1
    genesis = ledger.chain[0]
    assert genesis.event_type == "CASE_GENESIS"
    assert genesis.prev_hash == "0" * 64
    assert len(genesis.hash) == 64
    assert ledger.verify_integrity() is True

def test_append_events_and_chaining():
    ledger = AuditLedger("SC-TEST-002")
    
    e1 = ledger.append_event("MOTION_OPENED", "clerk", {"pr": "https://github.com/org/repo/pull/1"})
    assert e1.index == 1
    assert e1.prev_hash == ledger.chain[0].hash
    
    e2 = ledger.append_event("OBJECTION_FILED", "prosecutor", {"severity": "CRITICAL", "reason": "unmonitored"})
    assert e2.index == 2
    assert e2.prev_hash == e1.hash
    
    e3 = ledger.append_event("VERDICT_RENDERED", "Priya (Human Judge)", {"verdict": "CONDITIONS"})
    assert e3.index == 3
    assert e3.prev_hash == e2.hash

    assert len(ledger.chain) == 4
    assert ledger.verify_integrity() is True

def test_tamper_detection_in_payload():
    ledger = AuditLedger("SC-TEST-003")
    ledger.append_event("MOTION_OPENED", "clerk", {"pr": "pull/10"})
    e2 = ledger.append_event("VERDICT_RENDERED", "attacker", {"verdict": "APPROVED"})

    assert ledger.verify_integrity() is True

    # Malicious actor tampers with payload without recalculating hashes
    e2.payload["verdict"] = "TAMPERED_VERDICT"
    assert ledger.verify_integrity() is False

def test_tamper_detection_in_hash_link():
    ledger = AuditLedger("SC-TEST-004")
    ledger.append_event("EVIDENCE_LOGGED", "historian", {"incident": "INC-017"})
    e2 = ledger.append_event("VERDICT_RENDERED", "Priya", {"verdict": "REJECTED"})

    assert ledger.verify_integrity() is True

    # Malicious actor breaks parent hash pointer
    e2.prev_hash = "abcdef" * 10 + "1234"
    assert ledger.verify_integrity() is False

def test_export_audit_manifest():
    ledger = AuditLedger("SC-TEST-005")
    ledger.append_event("MOTION_OPENED", "clerk", {"pr": "pull/50"})
    ledger.append_event("VERDICT_RENDERED", "Priya", {"verdict": "CONDITIONS"})

    manifest = ledger.export_audit_manifest()
    assert manifest["case_id"] == "SC-TEST-005"
    assert manifest["total_events"] == 3
    assert manifest["is_valid"] is True
    assert len(manifest["events"]) == 3
    assert manifest["final_seal_hash"] == ledger.latest_entry.hash

