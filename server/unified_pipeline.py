"""Shared workflow service used by HTTP, CLI and platform adapters.

Live review uses retrieved GitHub evidence and the existing LLM engine. It ends
at AWAITING_VERDICT. No pipeline invocation can manufacture human approval.
"""
from dataclasses import asdict
import json
import threading
import uuid
from .authorization import default_authorization
from .case_manager import CaseManager
from .models import Case, CaseState, Verdict, VerdictType, Condition, Task, RollbackPlan, RollbackStatus, Objection, ObjectionSeverity, ObjectionStatus, Defense
from .switch_room import SwitchRoom
from .bridge_connector import ChatBridgeConnector
from .floor_controller import FloorRequestController
from .parallel_earth import ParallelEarthSimulator
from .live_courtroom_debate import LiveCourtroomDebateEngine
from .github_client import GitHubClient, GitHubOperations, parse_pr
from .store import Store


def restore_case(data):
    data = dict(data)
    data['state'] = CaseState(data['state'])
    data['objections'] = [Objection(**{**o, 'classification': ObjectionSeverity(o['classification']), 'status': ObjectionStatus(o['status'])}) for o in data['objections']]
    data['defenses'] = [Defense(**d) for d in data['defenses']]
    data['tasks'] = [Task(**t) for t in data['tasks']]
    if data['verdict']:
        v = data['verdict']
        data['verdict'] = Verdict(**{**v, 'type': VerdictType(v['type']), 'conditions': [Condition(**c) for c in v['conditions']]})
    if data['rollback_plan']:
        r = data['rollback_plan']
        data['rollback_plan'] = RollbackPlan(**{**r, 'execution_status': RollbackStatus(r['execution_status'])})
    return Case(**data)


class UnifiedBoardroomCourtPipeline:
    def __init__(self, room_name='ship-court', webhook_url=None, authorization=None, db_path=':memory:', github_client=None, debate_engine=None):
        self.authorization = authorization or default_authorization()
        self.store = Store(db_path)
        from .scope_coordinator import ScopeCoordinator
        self.scope = ScopeCoordinator(self.authorization, self.store)
        self.room = SwitchRoom(room_name, 'discord', authorization=self.authorization)
        self.manager = CaseManager(authorization=self.authorization)
        self.cases = self.manager.active_cases
        for data in self.store.list('case'):
            case = restore_case(data)
            if case.state == CaseState.EVIDENCE_COLLECTION:
                case.state = CaseState.CASE_OPENED
                self.store.put('case', case.case_id, case)
                self.store.event('court.review_interrupted', case.case_id, 'startup', {'retry_allowed': True})
            self.cases[case.case_id] = case
        self.bridge = ChatBridgeConnector(self.room, webhook_url=webhook_url, platform='discord')
        self.floor_controller = FloorRequestController(self.room, self.bridge, db_path=db_path)
        from .meetings import Meetings
        self.meetings = Meetings(self.authorization, self.store, self.floor_controller)
        self.parallel_earth = ParallelEarthSimulator(self.room, bridge=self.bridge)
        self.github_client = github_client or GitHubClient()
        self.github_ops = GitHubOperations(self.authorization, self.store, self.github_client)
        self.debate_engine = debate_engine or LiveCourtroomDebateEngine()
        import os
        from .research import ResearchService
        self.research = ResearchService(self.authorization, self.store, self.debate_engine,
            allowed_hosts=os.getenv("SHIPCOURT_RESEARCH_HOSTS", "").split(","))
        self.lock = threading.RLock()
        from .workspace import Workspace
        self.workspace = Workspace(self)

    def open_case(self, pr_url, services, principal):
        self.authorization.require(principal, role='operator')
        repo, number = parse_pr(pr_url)
        if not services or any(s not in self.parallel_earth.graph.nodes for s in services):
            raise ValueError('Specify services present in the configured dependency graph')
        evidence = self.github_client.evidence(pr_url)
        case = Case('SC-' + uuid.uuid4().hex, pr_url, repo, list(services), 'Not verified', change_summary=evidence['title'])
        with self.lock:
            self.cases[case.case_id] = case
            self.store.put('case', case.case_id, case)
            self.store.put('evidence', case.case_id, evidence)
            self.store.event('case.opened', case.case_id, principal.subject, {'pr_url': pr_url, 'head_sha': evidence['head_sha']}, actor_type='human')
        return case

    def attach_pull_request(self, case_id, pr_url, services, principal):
        self.authorization.require(principal, role='operator')
        repo, _ = parse_pr(pr_url)
        if not services or any(s not in self.parallel_earth.graph.nodes for s in services):
            raise ValueError('Known affected services required')
        evidence = self.github_client.evidence(pr_url)
        with self.lock:
            case = self.cases[case_id]
            if case.state != CaseState.CASE_OPENED:
                raise ValueError('Cannot change evidence after review has started')
            case.pr_url, case.repository, case.affected_services = pr_url, repo, services
            self.store.put('evidence', case_id, evidence)
            self.store.put('case', case_id, case)
            self.store.event('case.evidence_attached', case_id, principal.subject, {'pr_url': pr_url, 'head_sha': evidence['head_sha']})
            return case

    def review(self, case_id, principal):
        self.authorization.require(principal, role='operator')
        with self.lock:
            case = self.cases[case_id]
            if case.state != CaseState.CASE_OPENED:
                raise ValueError('Review is already running or complete')
            case.state = CaseState.EVIDENCE_COLLECTION
            self.store.put('case', case_id, case)
        try:
            evidence = self.store.get('evidence', case_id)
            incidents = self.manager.evidence_collector.search_incidents(case.affected_services[0])
            simulation = self.parallel_earth.run_simulation(case)
            context = json.dumps({'proposal': case.change_summary, 'evidence': evidence,
                                  'scope_evidence':[e for e in self.store.list('scope_evidence') if e['case_id']==case_id],
                                  'incident_fixtures_unverified': incidents, 'risk_model': asdict(simulation)})
            result = self.debate_engine.run_live_trial(context, repo=case.repository,
                                                      pr_number=str(evidence['pr_number']), judge_name='AI advisory reviewer')
            result['case_id'] = case_id
            result['binding_authorization'] = False
            self.store.put('advisory', case_id, result)
            self.store.put('simulation', case_id, simulation)
            case.state = CaseState.AWAITING_VERDICT
            self.store.event('court.advisory_completed', case_id, 'courtroom', {'advisory': result, 'authorization_required': True})
            return result
        except Exception as exc:
            case.state = CaseState.CASE_OPENED
            self.store.event('court.review_failed', case_id, 'courtroom', {'error_type': type(exc).__name__})
            raise
        finally:
            self.store.put('case', case_id, case)

    def decide(self, case_id, command, principal):
        with self.lock:
            brief = self.manager.record_verdict(case_id, command, principal=principal)
            case = self.cases[case_id]
            advisory = self.store.get('advisory', case_id)
            if advisory:
                brief += '\n\n## AI advisory (not authorization)\n' + advisory['prosecutor_indictment'] + '\n' + advisory['defender_rebuttal']
                case.release_brief = brief
            evidence = self.store.get('evidence', case_id) or {}
            model = self.store.get('simulation', case_id) or {}
            case.release_brief += '\n\n## Evidence provenance\nPR: ' + case.pr_url + '\nReviewed head: ' + evidence.get('head_sha', 'unknown') + '\nRisk analysis: ' + model.get('mode', 'unavailable') + '\nRollback execution: not performed.\n'
            brief = case.release_brief
            self.store.put('case', case_id, case)
            self.store.event('court.human_verdict', case_id, principal.subject, {'verdict': case.verdict.type.value}, actor_type='human')
            return brief

    def github_plan(self, case_id, principal):
        self.authorization.require(principal, role='operator')
        plan = self.github_ops.plan(self.cases[case_id], self.store.get('evidence', case_id))
        self.store.put('github_plan', case_id, plan)
        return plan

    def execute_github(self, case_id, principal, plan_hash):
        import hashlib
        plan = self.store.get('github_plan', case_id)
        if not plan or hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest() != plan_hash:
            raise ValueError('Review and approve the exact current plan hash')
        return self.github_ops.execute(plan, principal)

    def ingest_violation(self, event, principal):
        self.authorization.require(principal, role='hook', scope='hook:' + event['agent_id'])
        key = principal.subject + ':' + event['event_id']
        with self.workspace.lock, self.lock:
            existing = self.store.get('violation', key)
            if existing:
                return existing
            if event.get('decision_taken') not in ('BLOCK', 'ASK', 'WARN'):
                raise ValueError('Expected a scope guard violation decision')
            assignment=self.store.get('assignment',event['agent_id']) or {}
            mission=self.store.get('mission',assignment.get('mission_id',''))
            linked=self.cases.get(mission.get('case_id')) if mission else None
            # Only a server-provisioned assignment can attach a hook to a mission.
            case_id = linked.case_id if linked and linked.state==CaseState.CASE_OPENED else 'AG-' + uuid.uuid4().hex
            case = linked if linked and linked.case_id==case_id else Case(case_id, '', '', [], 'Not verified', change_summary=event['explanation'])
            self.cases[case_id] = case
            self.store.put('case', case_id, case)
            result = {'case_id': case_id, 'event_id': event['event_id'], 'status': 'ESCALATED',
                      'hook_enforcement': 'reported by authenticated hook; not independently observed'}
            self.store.put('violation', key, result)
            self.store.put('scope_evidence',key,{'case_id':case_id,'mission_id':mission['mission_id'] if mission else None,'event':event})
            if mission:
                with self.workspace.lock:
                    mission=self.store.get('mission',mission['mission_id'])
                    mission['evidence_refs'].append({'type':'antigravity_scope_event','event_id':event['event_id'],'case_id':case_id})
                    if not mission.get('case_id'):mission['case_id']=case_id
                    self.store.put('mission',mission['mission_id'],mission)
            self.store.event('developer.scope_violation_detected', case_id, principal.subject, event, source_platform='antigravity', actor_type='agent')
            notification_id=case_id+':'+event['event_id']
            self.store.put('switch_notification', notification_id, {'case_id': case_id, 'notification_id':notification_id,'status': 'PENDING',
                'content': json.dumps({'event': 'scope_violation', 'case_id': case_id,
                                       'agent_id': event['agent_id'], 'explanation': event['explanation']})})
            return result

    def execute_full_flowchart_run(self, *args, **kwargs):
        raise RuntimeError('Automatic canned approval removed. Use open_case, review, decide and separately approve the GitHub plan.')
