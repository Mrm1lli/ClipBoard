"""Execute only approved plans, with optimistic checks and recovery markers.

The remote API has no documented transactions/idempotency keys. Each create gets
an exact marker in its note so a lost response can be reconciled before retrying.
A local exclusive lock serializes our pipeline/executor processes. It cannot lock
out external CRM users: we re-read before writes and verify after each write.
"""
from contextlib import contextmanager
from filelock import FileLock, Timeout
from pathlib import Path
from .client import Client
from .matching import rank_candidates
from .pipeline import baseline
from .store import Store


@contextmanager
def workflow_lock(database):
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(database) + '.lock')
    try:
        lock.acquire(timeout=0)
    except Timeout as exc:
        raise RuntimeError('Another pipeline or CRM execution is running; retry later') from exc
    try:
        yield
    finally:
        lock.release()


def fields_equal(current, expected):
    return all(current.get(k) == v for k, v in expected.items())


def apply(database, key, client=None):
    with workflow_lock(database):
        store = Store(database)
        try:
            row = store.get(key)
            if row['state'] == 'applied':
                return  # harmless repeat request
            if row['state'] not in ('approved', 'applying'):
                raise ValueError('Explicit approval is required before CRM execution')
            choice = row['selected_choice']
            if choice is None:
                raise ValueError('No reviewed plan selected')
            bundle = row['payload']['choices'][choice]
            if row['state'] == 'approved':
                store.claim(key)
            crm = client or Client()
            _execute(store, key, bundle, crm)
            store.finish(key)
            with store.db:
                store.db.execute("UPDATE proposals SET execution_error='' WHERE id=?", (key,))
        except Exception:
            # Never persist raw exception text: HTTP errors may include sensitive data.
            with store.db:
                store.db.execute("UPDATE proposals SET execution_error='Execution stopped. Check baseline/operation journal and retry the approved plan after investigation.' WHERE id=? AND state='applying'", (key,))
            raise
        finally:
            store.close()


def _execute(store, key, bundle, crm):
    primary = bundle['primary']
    duplicate_plans = bundle.get('duplicates', [])
    kind = primary['kind']
    if kind not in ('update', 'no_change', 'duplicate', 'absent_from_website', 'create', 'change_of_ownership'):
        raise ValueError('Unsupported mutation plan')
    created = store.step_result(key, 'create_done')
    successor = created['id'] if created else bundle.get('survivor_id')

    # Check every impacted baseline before starting a fresh bundle, including losers.
    # On recovery, each operation independently validates its already-done state.
    started = store.step_result(key, 'preflight_done')
    if not started:
        for plan in [primary, *duplicate_plans]:
            if plan.get('before') and baseline(crm.get(plan['account_id'])) != plan['before']:
                raise RuntimeError('CRM baseline changed; generate and review a fresh proposal')
        store.record_step(key, 'preflight_done', {'ok': True})

    def patch_step(label, plan, changes):
        account_id = plan['account_id']
        expected = {**plan['before'], **changes}
        current = baseline(crm.get(account_id))
        if store.step_result(key, label + '_done'):
            if current != expected:
                raise RuntimeError('Previously applied record changed; manual review required')
            return
        intent = store.step_result(key, label + '_intent')
        if intent:
            if current == expected:
                store.record_step(key, label + '_done', {'account_id': account_id})
                return
        elif current != plan['before']:
            raise RuntimeError('CRM changed after review; refusing stale write')
        if current != plan['before']:
            raise RuntimeError('CRM changed during interrupted operation')
        if not intent:
            store.record_step(key, label + '_intent', {'changes': changes})
        crm.patch(account_id, changes)
        if baseline(crm.get(account_id)) != expected:
            raise RuntimeError('CRM read-back does not match approved changes')
        store.record_step(key, label + '_done', {'account_id': account_id})

    if kind in ('create', 'change_of_ownership'):
        marker = f'[bellhaven-sync:{key}:create]'
        desired = {**primary['create'], 'note': marker}
        intent = store.step_result(key, 'create_intent')
        all_accounts = crm.accounts()
        marked = [a for a in all_accounts if marker in a.get('note', '')]
        if len(marked) > 1:
            raise RuntimeError('Multiple records carry this operation marker; manual review required')
        if created:
            account = crm.get(created['id'])
            if not fields_equal(account, desired):
                raise RuntimeError('Created account no longer matches approved plan')
            successor = account['id']
        elif marked:
            if not intent or not fields_equal(marked[0], desired):
                raise RuntimeError('Unexpected record with this operation marker')
            successor = marked[0]['id']
            store.record_step(key, 'create_done', {'id': successor})
        else:
            # Prevent a second create if another run/user has already added the facility.
            excluded = {primary.get('account_id')} | {p['account_id'] for p in duplicate_plans}
            matches = rank_candidates(desired, [a for a in all_accounts if a['id'] not in excluded])
            if any(c.strong_address or c.strong_phone for c in matches):
                raise RuntimeError('A facility account now exists; re-run matching before creating')
            if kind == 'change_of_ownership' and baseline(crm.get(primary['account_id'])) != primary['before']:
                raise RuntimeError('Billing account changed before successor creation')
            if not intent:
                store.record_step(key, 'create_intent', {'fields': desired})
            account = crm.create(desired)
            successor = account['id']
            # Journal the ID before any follow-up read; retry can also discover the marker.
            store.record_step(key, 'create_done', {'id': successor})
            if not fields_equal(crm.get(successor), desired):
                raise RuntimeError('Created account failed read-back verification')
        if kind == 'change_of_ownership':
            patch_step('link_old', primary, {'cow_current_account': successor})
    elif kind != 'no_change':
        patch_step('primary', primary, primary['changes'])
    elif baseline(crm.get(primary['account_id'])) != primary['before']:
        raise RuntimeError('Surviving account changed before duplicate updates')

    for index, plan in enumerate(duplicate_plans):
        patch_step(f'duplicate_{index}', plan, {**plan['changes'], 'duplicate_of_account': successor})
