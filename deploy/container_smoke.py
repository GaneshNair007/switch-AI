"""Read-only container check: no provider calls or repository operations."""
import time
import urllib.request
import urllib.error


deadline=time.monotonic()+40
while True:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3) as response:
            assert response.status==200
        break
    except (OSError,urllib.error.URLError):
        if time.monotonic()>=deadline:raise
        time.sleep(1)
with urllib.request.urlopen('http://127.0.0.1:8080/',timeout=3) as response:
    html=response.read().decode()
    assert '<title>Ship Court' in html and 'Switch AI' not in html
try:
    urllib.request.urlopen('http://127.0.0.1:8080/api/hq',timeout=3)
except urllib.error.HTTPError as response:
    assert response.code==401
else:raise AssertionError('Unauthenticated workspace access must be rejected')
print('Container smoke passed: Ship Court serves health/UI and rejects unauthenticated workspace access.')
