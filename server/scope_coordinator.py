"""Coordinator endpoints compatible with the bundled Scope Guard client."""
import copy
from datetime import datetime, timezone
from pathlib import PurePosixPath
import threading
import time


class ScopeCoordinator:
    def __init__(self, authorization, store):
        self.auth, self.store = authorization, store
        self.lock = threading.RLock()

    def assignment(self, agent_id, principal):
        self.auth.require(principal, role='hook', scope='hook:' + agent_id)
        assignment = self.store.get('assignment', agent_id)
        if not assignment:
            raise KeyError('No assignment provisioned')
        return assignment

    def set_assignment(self, assignment, principal):
        agent_id = assignment['agent_id']
        self.auth.require(principal, scope=f'scope:{agent_id}:manage')
        if not assignment.get('task_id') or not isinstance(assignment.get('allowed_paths'), list):
            raise ValueError('Assignment task ID and allowed paths required')
        with self.lock:
            previous = self.store.get('assignment', agent_id)
            result = copy.deepcopy(assignment)
            result['assignment_version'] = (previous or {}).get('assignment_version', 0) + 1
            self.store.put('assignment', agent_id, result)
            self.store.event('scope.assignment', agent_id, principal.subject, result, actor_type='human')
            return result

    def request(self, request, principal):
        self.auth.require(principal, role='hook', scope='hook:' + request['agent_id'])
        with self.lock:
            existing = self.store.get('scope_request', request['request_id'])
            if existing:
                if existing['request']['agent_id'] != request['agent_id']:
                    raise PermissionError('Approval request belongs to another agent')
                return existing['response']
            assignment = self.assignment(request['agent_id'], principal)
            if request['current_version'] != assignment['assignment_version']:
                raise ValueError('Scope request uses a stale assignment')
            paths = request.get('requested_paths') or [request['target_path']]
            for path in paths:
                normalized = path.replace('\\','/')
                if PurePosixPath(normalized).is_absolute() or '..' in PurePosixPath(normalized).parts or any(c in normalized for c in ':*?['):
                    raise ValueError('Exceptions must name exact workspace-relative files')
            request = {**request, 'requested_paths': paths}
            response = {'request_id':request['request_id'],'status':'PENDING','approved_by':None,'updated_assignment':None}
            self.store.put('scope_request', request['request_id'], {'request':request,'response':response,'expires_at':time.time()+3600})
            return response

    def status(self, request_id, principal):
        record = self.store.get('scope_request', request_id)
        if not record:
            raise KeyError('Approval request not found')
        self.auth.require(principal, role='hook', scope='hook:' + record['request']['agent_id'])
        if record['response']['status'] == 'PENDING' and record['expires_at'] <= time.time():
            return {**record['response'],'status':'EXPIRED'}
        return record['response']

    def decide(self, request_id, approve, principal):
        if type(approve) is not bool:
            raise ValueError('Approval must be a boolean')
        with self.lock:
            record = self.store.get('scope_request', request_id)
            if not record:
                raise KeyError('Approval request not found')
            request = record['request']
            self.auth.require(principal, scope=f"scope:{request['agent_id']}:approve")
            if record['response']['status'] != 'PENDING':
                return record['response']
            if record['expires_at'] <= time.time():
                raise ValueError('Approval request expired')
            assignment = self.store.get('assignment',request['agent_id'])
            if assignment['assignment_version'] != request['current_version']:
                raise ValueError('Assignment changed; request a fresh exception')
            if approve:
                assignment['exceptions'] = sorted(set(assignment.get('exceptions',[])) | set(request['requested_paths']))
                assignment['assignment_version'] += 1
                self.store.put('assignment',request['agent_id'],assignment)
            response={'request_id':request_id,'status':'APPROVED' if approve else 'REJECTED','approved_by':principal.subject,
                      'updated_assignment':assignment if approve else None,'timestamp':datetime.now(timezone.utc).isoformat()}
            record['response']=response
            self.store.put('scope_request',request_id,record)
            self.store.event('scope.human_decision',request_id,principal.subject,response,actor_type='human')
            return response
