"""Short-lived HttpOnly dashboard sessions with CSRF protection."""
from http.cookies import SimpleCookie, CookieError
import secrets
import threading
import time


class DashboardSessions:
    def __init__(self, auth):
        self.auth, self.sessions, self.lock = auth, {}, threading.RLock()

    def login(self, credential):
        principal = self.auth.authenticate('Bearer ' + credential)
        if not principal.roles.intersection({'operator','viewer'}):
            self.auth.revoke(principal)
            raise PermissionError('Dashboard access required')
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.sessions = {k:v for k,v in self.sessions.items() if v['principal'].expires_at > time.time()}
            self.sessions[token] = {'principal':principal,'csrf':secrets.token_urlsafe(32)}
        return token

    def resolve(self, cookie, csrf=None, mutation=False):
        parsed = SimpleCookie()
        try:parsed.load(cookie or '')
        except CookieError as exc:raise PermissionError('Invalid session cookie') from exc
        token = parsed.get('shipcourt_session')
        record = self.sessions.get(token.value if token else '')
        if not record or record['principal'].expires_at <= time.time():
            raise PermissionError('Sign in required')
        p = record['principal']
        with self.auth._lock:
            if self.auth._sessions.get(p.session_id) is not p:
                raise PermissionError('Session revoked')
        if mutation and not secrets.compare_digest(csrf or '', record['csrf']):
            raise PermissionError('CSRF check failed')
        return record

    def logout(self, cookie, csrf):
        self.auth.revoke(self.resolve(cookie,csrf,True)['principal'])
