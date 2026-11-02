import copy
import tempfile
import unittest
from pathlib import Path
from bellhaven.executor import apply, workflow_lock
from bellhaven.planning import plan_update
from bellhaven.store import Store


class FakeCRM:
    def __init__(self, records):
        self.records = {a['id']: copy.deepcopy(a) for a in records}
        self.writes = []
        self.lose_create_response = False
        self.lose_patch_response = False

    def accounts(self):
        return copy.deepcopy(list(self.records.values()))

    def get(self, key):
        return copy.deepcopy(self.records[key])

    def create(self, fields):
        key = f'new-{len(self.records)}'
        self.records[key] = dict(fields, id=key)
        self.writes.append(('create', key))
        if self.lose_create_response:
            self.lose_create_response = False
            raise TimeoutError('Response lost after successful remote create')
        return self.get(key)

    def patch(self, key, fields):
        self.records[key].update(fields)
        self.writes.append(('patch', key))
        if self.lose_patch_response:
            self.lose_patch_response = False
            raise TimeoutError('Response lost after successful patch')


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'review.sqlite3')
        self.store = Store(self.path)
        self.location = dict(name='Bellhaven Test', address='1 Main St', city='Town', state='OH', zip='12345', care_offerings='Assisted Living')
        self.old = dict(self.location, id='old', parent_id='previous', lifetime_revenue=100, outstanding_ar=20, status='Active', note='', cow_current_account='')
        self.crm = FakeCRM([self.old])

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def proposal(self, primary, approve=True):
        key = self.store.propose({'kind': primary['kind'], 'choices': [{'survivor_id': 'old', 'primary': primary, 'duplicates': []}]})
        if approve:
            self.store.decide(key, 'approved', choice=0)
        return key

    def test_review_app_approval_executes_and_rerun_has_no_proposal(self):
        from bellhaven.web import create_app
        from bellhaven.pipeline import generate
        old = dict(self.old, outstanding_ar=0)
        self.crm = FakeCRM([old])
        plan = plan_update(self.location, old, 'correct')
        key = self.proposal(plan, False)
        app = create_app(self.path, execute=lambda path, proposal: apply(path, proposal, self.crm))
        app.testing = True
        client = app.test_client()
        self.assertEqual(client.get('/').status_code, 200)
        with client.session_transaction() as session:
            csrf = session['csrf']
        response = client.post(f'/proposals/{key}/decision', data={'csrf': csrf, 'decision': 'approved', 'choice': '0'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store.get(key)['state'], 'applied')
        self.assertEqual(self.crm.get('old')['parent_id'], 'correct')
        location = dict(self.location, care_offerings=['Assisted Living'], phone='')
        parent = dict(id='correct', name='Bellhaven Senior Living (Parent Account)', parent_id='', address='')
        proposals, _ = generate({'locations': [location], 'directory_pages': 1}, [parent, self.crm.get('old')])
        self.assertEqual(proposals, [])

    def test_concurrent_workflow_is_blocked(self):
        with workflow_lock(self.path):
            with self.assertRaises(RuntimeError):
                with workflow_lock(self.path):
                    self.fail('Second workflow acquired the lock')

    def test_unapproved_never_writes(self):
        key = self.proposal(plan_update(self.location, self.old, 'correct'), False)
        with self.assertRaises(ValueError):
            apply(self.path, key, self.crm)
        self.assertEqual(self.crm.writes, [])

    def test_protected_ownership_preserves_billing_and_parent(self):
        key = self.proposal(plan_update(self.location, self.old, 'correct'))
        apply(self.path, key, self.crm)
        updated = self.crm.get('old')
        self.assertEqual(updated['parent_id'], 'previous')
        self.assertEqual(updated['lifetime_revenue'], 100)
        self.assertEqual(updated['outstanding_ar'], 20)
        successor = self.crm.get(updated['cow_current_account'])
        self.assertEqual(successor['parent_id'], 'correct')
        self.assertNotIn('lifetime_revenue', successor)
        self.assertEqual(self.store.get(key)['state'], 'applied')
        apply(self.path, key, self.crm)
        self.assertEqual(len(self.crm.writes), 2)

    def test_create_timeout_recovery_does_not_duplicate(self):
        key = self.proposal(plan_update(self.location, self.old, 'correct'))
        self.crm.lose_create_response = True
        with self.assertRaises(TimeoutError):
            apply(self.path, key, self.crm)
        self.assertEqual(self.store.get(key)['state'], 'applying')
        apply(self.path, key, self.crm)
        self.assertEqual(sum(w[0] == 'create' for w in self.crm.writes), 1)
        self.assertEqual(self.store.get(key)['state'], 'applied')

    def test_patch_timeout_recovery_does_not_repeat_patch(self):
        old = dict(self.old, outstanding_ar=0)
        self.crm = FakeCRM([old])
        key = self.proposal(plan_update(self.location, old, 'correct'))
        self.crm.lose_patch_response = True
        with self.assertRaises(TimeoutError):
            apply(self.path, key, self.crm)
        apply(self.path, key, self.crm)
        self.assertEqual(self.crm.writes, [('patch', 'old')])

    def test_stale_review_blocks_all_writes(self):
        key = self.proposal(plan_update(self.location, self.old, 'correct'))
        self.crm.records['old']['outstanding_ar'] = 99
        with self.assertRaises(RuntimeError):
            apply(self.path, key, self.crm)
        self.assertEqual(self.crm.writes, [])

    def test_external_create_blocks_new_duplicate(self):
        primary = {'kind': 'create', 'create': dict(self.location, parent_id='correct', status='Active')}
        key = self.proposal(primary)
        with self.assertRaises(RuntimeError):
            apply(self.path, key, self.crm)
        self.assertEqual(self.crm.writes, [])


if __name__ == '__main__':
    unittest.main()
