import tempfile
import unittest
from pathlib import Path
from bellhaven.store import Store
from bellhaven.web import create_app


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = str(Path(self.tmp.name) / 'review.sqlite3')
        self.path = path
        self.store = Store(path)
        self.key = self.store.propose({'kind': 'update', 'reason': 'Test', 'choices': [{'primary': {'kind': 'update', 'before': {'name': 'Old'}, 'changes': {'name': '<script>bad()</script>'}}, 'duplicates': []}]})
        self.executions = []
        app = create_app(path, execute=lambda database, key: self.executions.append(key))
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_review_then_reject_persists(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Reject proposal', page.data)
        self.assertNotIn(b'<script>bad()</script>', page.data)
        with self.client.session_transaction() as session:
            csrf = session['csrf']
        response = self.client.post(f'/proposals/{self.key}/decision', data={'csrf': csrf, 'decision': 'rejected', 'note': 'Not the same facility'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.store.get(self.key)['state'], 'rejected')
        self.assertIn(b'Not the same facility', self.client.get('/?state=rejected').data)

    def test_execution_not_started_keeps_approved_plan_visible(self):
        def blocked(database, key):
            raise RuntimeError('Another workflow holds the lock')
        app = create_app(self.path, execute=blocked)
        app.testing = True
        client = app.test_client()
        client.get('/')
        with client.session_transaction() as session:
            csrf = session['csrf']
        result = client.post(f'/proposals/{self.key}/decision', data={'csrf': csrf, 'decision': 'approved', 'choice': '0'}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Approved but not started', result.data)
        self.assertEqual(self.store.get(self.key)['state'], 'approved')

    def test_cross_site_and_duplicate_decisions_blocked(self):
        self.assertEqual(self.client.post(f'/proposals/{self.key}/decision', data={'decision': 'approved'}).status_code, 400)
        self.client.get('/')
        with self.client.session_transaction() as session:
            csrf = session['csrf']
        data = {'csrf': csrf, 'decision': 'approved', 'choice': '0'}
        self.assertEqual(self.client.post(f'/proposals/{self.key}/decision', data=data).status_code, 302)
        self.assertEqual(self.client.post(f'/proposals/{self.key}/decision', data=data).status_code, 409)
        self.assertEqual(self.executions, [self.key])


if __name__ == '__main__':
    unittest.main()
