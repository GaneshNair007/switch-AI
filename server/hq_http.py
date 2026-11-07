"""Dashboard session and shared-workspace HTTP adapter."""
from .dashboard_auth import DashboardSessions


def sessions(handler):
    cls=type(handler)
    auth=(handler.workflow or handler.mgr).authorization
    if not getattr(cls,'dashboard_sessions',None) or cls.dashboard_sessions.auth is not auth:
        cls.dashboard_sessions=DashboardSessions(auth)
    return cls.dashboard_sessions


def origin(handler):
    value=handler.headers.get('Origin');host=handler.headers.get('Host','')
    if value and value not in ('http://'+host,'https://'+host):
        raise PermissionError('Cross-origin request rejected')


def principal(handler):
    bearer=handler.headers.get('Authorization')
    if bearer:
        return (handler.workflow or handler.mgr).authorization.authenticate(bearer)
    origin(handler)
    return sessions(handler).resolve(handler.headers.get('Cookie'),handler.headers.get('X-CSRF-Token'),handler.command!='GET')['principal']


def get(handler):
    if handler.path not in ('/api/auth/me','/api/hq'):
        return False
    try:
        if handler.path=='/api/auth/me':
            record=sessions(handler).resolve(handler.headers.get('Cookie'));p=record['principal']
            result={'identity':p.subject,'roles':sorted(p.roles),'csrf':record['csrf'],'expires_at':p.expires_at}
        else:
            result=handler.workflow.workspace.snapshot(principal(handler))
        handler._json_response(200,result)
    except PermissionError:
        handler._json_response(401,{'error':'Sign in required'})
    return True


def post(handler,body):
    if handler.path not in ('/api/auth/login','/api/auth/logout','/api/hq/action'):
        return False
    try:
        origin(handler)
        if handler.path=='/api/hq/action':
            handler._json_response(200,handler.workflow.workspace.action(body['action'],body.get('args',{}),principal(handler)))
        else:
            if handler.path.endswith('/login'):
                token=sessions(handler).login(body.get('credential',''))
                cookie='shipcourt_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=300'
            else:
                sessions(handler).logout(handler.headers.get('Cookie'),handler.headers.get('X-CSRF-Token'))
                cookie='shipcourt_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
            if handler.headers.get('Host','').split(':')[0] not in ('localhost','127.0.0.1'):
                cookie+='; Secure'
            handler.send_response(200);handler.send_header('Content-Type','application/json')
            handler.send_header('Cache-Control','no-store');handler.send_header('Set-Cookie',cookie);handler.end_headers()
            handler.wfile.write(b'{"ok":true}')
    except PermissionError:
        handler._json_response(403,{'error':'Permission or CSRF check failed'})
    except (KeyError,ValueError,TypeError) as exc:
        handler._json_response(400,{'error':str(exc)})
    except Exception as exc:
        handler._json_response(502,{'error':type(exc).__name__,'detail':'Operation failed; inspect the audit ledger'})
    return True
