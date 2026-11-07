"""Opt-in observation of an operator-configured staging health endpoint.

Never injects failures or executes rollback. Results describe only the sampled
endpoint, not deployment-wide correctness or rollback recovery.
"""
import math
import time
import urllib.parse
import urllib.request
import urllib.error


def measure_staging(url, samples=10, opener=None, clock=time.perf_counter):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or not parsed.hostname:
        raise ValueError('Valid staging URL required')
    if not isinstance(samples, int) or isinstance(samples, bool) or not 1 <= samples <= 100:
        raise ValueError('Samples must be between 1 and 100')
    opener = opener or urllib.request.urlopen
    latencies, statuses, errors = [], [], []
    for _ in range(samples):
        started = clock()
        try:
            with opener(urllib.request.Request(url, method='GET'), timeout=5) as response:
                statuses.append(response.status)
                response.read(1024)
        except urllib.error.HTTPError as exc:
            statuses.append(exc.code)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            statuses.append(None)
            errors.append(type(exc).__name__)
        latencies.append((clock() - started) * 1000)
    ordered = sorted(latencies)
    return {'mode': 'OBSERVED_STAGING', 'endpoint': url, 'samples': samples,
            'success_rate': sum(status is not None and 200 <= status < 300 for status in statuses) / samples * 100,
            'p99_latency_ms': ordered[max(0, math.ceil(samples * .99)-1)], 'statuses': statuses,
            'errors': errors, 'rollback_executed': False, 'rollback_recovery_seconds': None,
            'limitations': 'Sequential GET samples only; no canary configuration or rollback measured'}
