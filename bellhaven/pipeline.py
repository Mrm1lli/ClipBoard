"""Daily read-only discovery: complete scrape -> complete CRM -> review proposals."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from .client import Client
from .matching import classify, rank_candidates, normalize
from .planning import plan_update, plan_duplicate, plan_absent
from .scraper import scrape
from .store import Store

CARE_MAP = {'Short-Term Rehabilitation & Nursing': 'Skilled Nursing',
            'Memory Support': 'Memory Care', 'Assisted Living': 'Assisted Living'}


def crm_location(location):
    # Preserve website labels in evidence; use the CRM's existing care vocabulary.
    return {**{k: location[k] for k in ('name', 'address', 'city', 'state', 'zip')},
            'care_offerings': '; '.join(CARE_MAP[label] for label in location['care_offerings'])}


def baseline(account):
    # updated_at and parent_name are server-derived; neither changes intent.
    return {k: v for k, v in account.items() if k not in ('updated_at', 'parent_name', 'created_by_candidate')}


def evidence(location):
    return {k: v for k, v in location.items() if k not in ('source_sha256', 'collected_at')}


def reconciliation(location, survivor, others, parent_id):
    primary = plan_update(crm_location(location), baseline(survivor), parent_id)
    duplicates = [plan_duplicate(baseline(row), baseline(survivor)) for row in others]
    return {'survivor_id': survivor['id'], 'primary': primary, 'duplicates': duplicates}


def generate(snapshot, accounts):
    parents = [a for a in accounts if a['name'] == 'Bellhaven Senior Living (Parent Account)' and not a.get('parent_id')]
    if len(parents) != 1:
        raise ValueError('Cannot unambiguously identify Bellhaven parent')
    parent = parents[0]['id']
    facilities = [a for a in accounts if a['id'] != parent and a.get('address')]
    by_id = {a['id']: a for a in facilities}
    used = set()
    proposals = []
    report = []
    for location in snapshot['locations']:
        result = classify(location, facilities)
        ranked = rank_candidates(location, facilities)
        same_address = [c for c in ranked if c.strong_address]
        candidates = [by_id[c.account_id] for c in same_address]
        if result['classification'] == 'matched' and result['account_id'] not in {a['id'] for a in candidates}:
            candidates.insert(0, by_id[result['account_id']])  # name + phone resolves PO box
        if candidates:
            ids = {a['id'] for a in candidates}
            if used & ids:
                raise ValueError('An account matches multiple website locations; manual investigation required')
            used |= ids
            if len(candidates) > 1:
                # Recommendation, never silent selection: the UI requires a specific survivor.
                candidates.sort(key=lambda a: (a.get('phone') != location.get('phone'),
                    not (a.get('lifetime_revenue', 0) or a.get('outstanding_ar', 0)),
                    a.get('parent_id') != parent, normalize(a['name']) != normalize(location['name']), a['id']))
                choices = [reconciliation(location, row, [a for a in candidates if a['id'] != row['id']], parent) for row in candidates]
                proposals.append({'kind': 'duplicate_group', 'reason': 'Multiple active accounts share this facility address. Choose the surviving account explicitly; confirm duplicates before approval.',
                    'evidence': evidence(location), 'candidates': [{**c.__dict__, 'account': baseline(by_id[c.account_id])} for c in ranked if c.account_id in ids],
                    'choices': choices})
                category = 'duplicate_group'
            else:
                choice = reconciliation(location, candidates[0], [], parent)
                category = choice['primary']['kind']
                if category != 'no_change':
                    proposals.append({'kind': category, 'reason': choice['primary'].get('reason', 'Website evidence supports correcting the existing account.'),
                        'evidence': evidence(location), 'candidates': [{**c, 'account': baseline(by_id[c['account_id']])} for c in result['candidates']], 'choices': [choice]})
            report.append({'location': location['name'], 'classification': category, 'account_ids': sorted(ids)})
        elif result['classification'] == 'missing':
            proposals.append({'kind': 'create', 'reason': 'No confident existing CRM match found. Compare candidate addresses and identities before creating; reject if an existing account should be investigated instead.',
                'evidence': evidence(location), 'candidates': [{**c, 'account': baseline(by_id[c['account_id']])} for c in result['candidates']],
                'choices': [{'primary': {'kind': 'create', 'create': {**crm_location(location), 'parent_id': parent, 'status': 'Active'}}, 'duplicates': []}]})
            report.append({'location': location['name'], 'classification': 'missing'})
        else:
            ids = {c['account_id'] for c in result['candidates'] if c['score'] >= 40}
            used |= ids
            proposals.append({'kind': 'ambiguous', 'reason': 'Insufficient identity evidence. Reject and investigate; no CRM mutation is available.',
                'evidence': evidence(location), 'candidates': [{**c, 'account': baseline(by_id[c['account_id']])} for c in result['candidates']], 'choices': []})
            report.append({'location': location['name'], 'classification': 'ambiguous'})
    for account in facilities:
        if account['id'] in used or account.get('parent_id') != parent or account.get('duplicate_of_account') or account.get('cow_current_account'):
            continue
        if account.get('status') == 'Needs Review':
            continue
        plan = plan_absent(baseline(account))
        plan['changes']['note'] = (account.get('note', '') + '\nNot listed on the complete Bellhaven website snapshot. Ownership/closure requires verification.').strip()
        proposals.append({'kind': 'absent_from_website', 'reason': plan['reason'],
            'evidence': {'complete_website_count': len(snapshot['locations']), 'directory_pages': snapshot['directory_pages']},
            'choices': [{'primary': plan, 'duplicates': []}]})
    return proposals, report


def run(database='data/review.sqlite3', client=None):
    snapshot = scrape()
    accounts = (client or Client()).accounts()
    proposals, report = generate(snapshot, accounts)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory = Path('data/runs') / timestamp
    directory.mkdir(parents=True)
    (directory / 'website.json').write_text(json.dumps(snapshot, indent=2))
    (directory / 'accounts.json').write_text(json.dumps(accounts, indent=2))
    (directory / 'report.json').write_text(json.dumps(report, indent=2))
    store = Store(database)
    try:
        keys = {store.propose(p) for p in proposals}
        with store.db:
            for row in store.list():
                if row['state'] == 'pending' and row['id'] not in keys:
                    store.db.execute("UPDATE proposals SET state='superseded' WHERE id=?", (row['id'],))
        summary = {'locations': len(snapshot['locations']), 'accounts': len(accounts),
                   'classifications': dict(Counter(r['classification'] for r in report)),
                   'proposal_count': len(proposals), 'queue': dict(Counter(p['state'] for p in store.list())),
                   'run_directory': str(directory)}
        (directory / 'summary.json').write_text(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()
