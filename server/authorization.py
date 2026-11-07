"""Fail-closed identity authorization. Credentials are provisioned server-side.

SHIPCOURT_IDENTITIES is a JSON array of {id, token_sha256, roles, scopes}.
Raw credentials never appear in state, audit events, or errors. Transport adapters
must authenticate before passing the resulting opaque session to domain services.
"""
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import secrets
import threading
import time


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset
    scopes: frozenset
    session_id: str
    expires_at: float


class AuthorizationService:
    def __init__(self, identities=None, clock=time.time):
        self.identities = list(identities if identities is not None else json.loads(os.getenv('SHIPCOURT_IDENTITIES', '[]')))
        self.clock = clock
        self._sessions = {}
        self._lock = threading.RLock()
        for identity in self.identities:
            if not identity.get('id') or len(identity.get('token_sha256', '')) != 64:
                raise ValueError('Each identity requires an id and SHA-256 credential digest')

    def authenticate(self, authorization):
        if not isinstance(authorization, str) or not authorization.startswith('Bearer '):
            raise PermissionError('Authentication required')
        token = authorization[7:]
        if len(token) < 32:
            raise PermissionError('Invalid credential')
        digest = hashlib.sha256(token.encode()).hexdigest()
        for identity in self.identities:
            if hmac.compare_digest(digest, identity['token_sha256']):
                if identity.get('disabled'):
                    break
                with self._lock:
                    now = self.clock()
                    self._sessions = {k: p for k, p in self._sessions.items() if p.expires_at > now}
                    principal = Principal(identity['id'], frozenset(identity.get('roles', [])),
                                          frozenset(identity.get('scopes', [])), secrets.token_urlsafe(32), now + 300)
                    self._sessions[principal.session_id] = principal
                    return principal
        raise PermissionError('Invalid credential')

    def require(self, principal, role='approver', scope=None):
        with self._lock:
            if (not isinstance(principal, Principal)
                    or self._sessions.get(principal.session_id) is not principal
                    or principal.expires_at <= self.clock()
                    or role not in principal.roles
                    or (scope and scope not in principal.scopes and '*' not in principal.scopes)):
                raise PermissionError('Security violation: authenticated identity and scoped role required')
        return principal

    def revoke(self, principal):
        with self._lock:
            self._sessions.pop(principal.session_id, None)


_default = None

def default_authorization():
    global _default
    if _default is None:
        _default = AuthorizationService()
    return _default
