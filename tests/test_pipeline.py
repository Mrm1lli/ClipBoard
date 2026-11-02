import unittest
from bellhaven.pipeline import generate


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.parent = dict(id='parent', name='Bellhaven Senior Living (Parent Account)', parent_id='', address='')
        self.location = dict(name='Bellhaven Test', address='1 Main Street', city='Town', state='OH', zip='12345',
                             care_offerings=['Assisted Living'], phone='1234567890', source_url='https://example.test/community', source_sha256='hash')
        self.account = dict(id='facility', name='Bellhaven Test', address='1 Main Street', city='Town', state='OH', zip='12345',
                            care_offerings='Assisted Living', phone='1234567890', parent_id='parent', status='Active',
                            lifetime_revenue=0, outstanding_ar=0, duplicate_of_account='', cow_current_account='', note='')
        self.snapshot = {'locations': [self.location], 'directory_pages': 1}

    def test_correct_match_has_no_mutation(self):
        proposals, report = generate(self.snapshot, [self.parent, self.account])
        self.assertEqual(proposals, [])
        self.assertEqual(report[0]['classification'], 'no_change')

    def test_duplicate_group_requires_explicit_survivor_choices(self):
        other = dict(self.account, id='duplicate', phone='0000000000')
        proposals, _ = generate(self.snapshot, [self.parent, self.account, other])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]['kind'], 'duplicate_group')
        self.assertEqual(len(proposals[0]['choices']), 2)
        self.assertEqual(proposals[0]['choices'][0]['survivor_id'], 'facility')
        self.assertEqual(proposals[0]['choices'][0]['duplicates'][0]['changes']['status'], 'Inactive')

    def test_historical_linked_accounts_do_not_reappear_as_absent(self):
        historical = dict(self.account, id='historical', address='Old Street', cow_current_account='facility')
        proposals, _ = generate(self.snapshot, [self.parent, self.account, historical])
        self.assertEqual(proposals, [])

    def test_absence_is_review_only_and_preserves_parent(self):
        absent = dict(self.account, id='absent', name='Elsewhere', address='99 Elsewhere', city='Other')
        proposals, _ = generate(self.snapshot, [self.parent, self.account, absent])
        plan = proposals[0]['choices'][0]['primary']
        self.assertEqual(plan['changes']['status'], 'Needs Review')
        self.assertNotIn('parent_id', plan['changes'])

    def test_changed_scrape_hash_does_not_change_proposal_identity(self):
        account = dict(self.account, parent_id='other')
        first, _ = generate(self.snapshot, [self.parent, account])
        self.location['source_sha256'] = 'new-hash'
        second, _ = generate(self.snapshot, [self.parent, account])
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
