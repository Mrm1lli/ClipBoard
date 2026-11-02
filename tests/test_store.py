import tempfile
import unittest
from pathlib import Path
from bellhaven.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'review.sqlite3')
        self.store = Store(self.path)
        self.payload = {'kind': 'update', 'account_id': '123', 'changes': {'parent_id': 'bellhaven'}}

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_decisions_survive_restart_and_identical_rerun(self):
        for decision in ('approved', 'rejected'):
            payload = dict(self.payload, account_id=decision)
            key = self.store.propose(payload)
            self.store.decide(key, decision)
            self.store.close()
            self.store = Store(self.path)
            self.assertEqual(self.store.propose(payload), key)
            self.assertEqual(self.store.get(key)['state'], decision)
        self.assertEqual(len(self.store.list()), 2)

    def test_new_evidence_requires_new_decision(self):
        key = self.store.propose(self.payload)
        self.store.decide(key, 'rejected')
        changed = self.store.propose(dict(self.payload, changes={'parent_id': 'different'}))
        self.assertNotEqual(key, changed)
        self.assertEqual(self.store.get(changed)['state'], 'pending')

    def test_cannot_apply_without_approval(self):
        key = self.store.propose(self.payload)
        with self.assertRaises(ValueError):
            self.store.claim(key)
        self.store.decide(key, 'rejected')
        with self.assertRaises(ValueError):
            self.store.claim(key)

    def test_single_execution_claim_and_persistent_journal(self):
        key = self.store.propose(self.payload)
        self.store.decide(key, 'approved')
        self.store.claim(key)
        with self.assertRaises(ValueError):
            self.store.claim(key)
        self.store.record_step(key, 'create', {'id': 'new-account'})
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.step_result(key, 'create'), {'id': 'new-account'})
        self.store.finish(key)
        self.assertEqual(self.store.get(key)['state'], 'applied')

    def test_decision_cannot_be_overwritten(self):
        key = self.store.propose(self.payload)
        self.store.decide(key, 'rejected')
        with self.assertRaises(ValueError):
            self.store.decide(key, 'approved')


if __name__ == '__main__':
    unittest.main()
