"""Small HTTPS CRM client; credentials are sent only to the assessment host."""
import json
import os
from urllib.parse import urlencode, urlsplit, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

BASE = 'https://analyst-assessment-production.up.railway.app'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # never forward Authorization to a redirected host


class Client:
    def __init__(self):
        self.token = os.environ.get('BELLHAVEN_API_TOKEN')
        if not self.token:
            raise RuntimeError('Set BELLHAVEN_API_TOKEN securely before using the CRM')
        self.opener = build_opener(NoRedirect)

    def request(self, method, path, payload=None):
        if not path.startswith('/api/v1/'):
            raise ValueError('CRM path must be under /api/v1/')
        body = json.dumps(payload).encode() if payload is not None else None
        req = Request(BASE + path, data=body, method=method,
                      headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        # No automatic retries of writes: a timeout can hide a successful mutation.
        with self.opener.open(req, timeout=30) as response:
            return json.load(response)

    def accounts(self):
        records = []
        total = None
        page = 1
        while True:
            result = self.request('GET', '/api/v1/accounts?' + urlencode({'page': page, 'page_size': 50}))
            if result['page'] != page or not result['data'] and len(records) != result['total']:
                raise RuntimeError('Incomplete account pagination')
            if total is not None and result['total'] != total:
                raise RuntimeError('Account count changed during pagination; retry the read')
            total = result['total']
            records.extend(result['data'])
            if len(records) >= total:
                break
            page += 1
            if page > 1000:
                raise RuntimeError('Pagination exceeded safety limit')
        if len(records) != total or len({a['account_id'] for a in records}) != total:
            raise RuntimeError('CRM snapshot is incomplete or contains repeated IDs')
        return [canonical_account(a) for a in records]

    def get(self, account_id):
        result = self.request('GET', '/api/v1/accounts/' + quote(str(account_id), safe=''))
        return canonical_account(result.get('data', result))

    def patch(self, account_id, changes):
        return self.request('PATCH', '/api/v1/accounts/' + quote(str(account_id), safe=''), api_fields(changes))

    def create(self, fields):
        result = self.request('POST', '/api/v1/accounts', api_fields(fields))
        return canonical_account(result.get('data', result))


FIELD_MAP = {'id': 'account_id', 'address': 'billing_street', 'city': 'billing_city',
             'state': 'billing_state', 'zip': 'billing_zip', 'care_offerings': 'care_type',
             'cow_current_account': 'chow_current_account'}


def canonical_account(raw):
    reverse = {v: k for k, v in FIELD_MAP.items()}
    return {reverse.get(k, k): v for k, v in raw.items()}


def api_fields(fields):
    return {FIELD_MAP.get(k, k): v for k, v in fields.items()}
