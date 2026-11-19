"""Verify actual public routing after deployment, without creating user data."""
import sys
from urllib.parse import urljoin, urlparse

import requests


def main():
    if len(sys.argv) != 2:
        print('Usage: python scripts/check_public_routes.py https://YOUR_DOMAIN')
        return 2
    base = sys.argv[1].rstrip('/') + '/'
    if urlparse(base).scheme != 'https' or not urlparse(base).netloc:
        print('Use the public HTTPS deployment origin.')
        return 2
    failures = 0
    with requests.Session() as client:
        checks = (
            ('/', lambda r: r.status_code in (307, 308) and
             urljoin(base, r.headers.get('Location', '')) == urljoin(base, 'dashboard')),
            ('/dashboard', lambda r: r.status_code == 200 and 'Lumen' in r.text),
            ('/logos/AAPL.png', lambda r: r.status_code == 200 and r.headers.get('Content-Type', '').startswith('image/')),
            ('/api/health', lambda r: r.status_code == 200 and r.json().get('status') == 'ok'),
            ('/api/auth/me', lambda r: r.status_code == 401),
        )
        for path, valid in checks:
            try:
                response = client.get(urljoin(base, path), timeout=20, allow_redirects=False)
                passed = valid(response)
                print(f'{"PASS" if passed else "FAIL"} {path} (HTTP {response.status_code})')
            except (requests.RequestException, ValueError):
                passed = False
                print(f'FAIL {path} (request failed)')
            failures += not passed
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
