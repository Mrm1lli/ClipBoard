import unittest
from bellhaven.matching import classify
from bellhaven.planning import plan_update, plan_duplicate


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.location = dict(name='Bellhaven Oak Grove', address='123 North Main Street',
                             city='Austin', state='TX', zip='78701', care_offerings=['Memory Care'])
        self.account = dict(self.location, id='a', parent_id='old', lifetime_revenue=100, outstanding_ar=25)

    def test_abbreviations_match_even_with_outdated_name(self):
        account = dict(self.account, name='Oak Grove Senior Living', address='123 N Main St.')
        self.assertEqual(classify(self.location, [account])['classification'], 'matched')

    def test_name_alone_is_not_confident(self):
        account = dict(self.account, address='999 Elsewhere Road', city='Dallas', zip='75001')
        self.assertNotEqual(classify(self.location, [account])['classification'], 'matched')

    def test_colocated_accounts_require_review(self):
        self.assertEqual(classify(self.location, [self.account, dict(self.account, id='b')])['classification'], 'ambiguous')

    def test_conflicting_state_is_not_confident(self):
        self.assertNotEqual(classify(self.location, [dict(self.account, state='CA')])['classification'], 'matched')

    def test_billing_account_is_preserved(self):
        original = dict(self.account)
        plan = plan_update(self.location, self.account, 'bellhaven')
        self.assertEqual(plan['kind'], 'change_of_ownership')
        self.assertEqual(plan['create']['parent_id'], 'bellhaven')
        self.assertNotIn('lifetime_revenue', plan['create'])
        self.assertNotIn('changes', plan)
        self.assertEqual(self.account, original)

    def test_direct_reparent_when_either_billing_condition_is_zero(self):
        for field in ('lifetime_revenue', 'outstanding_ar'):
            with self.subTest(field=field):
                plan = plan_update(self.location, dict(self.account, **{field: 0}), 'bellhaven')
                self.assertEqual(plan['kind'], 'update')
                self.assertEqual(plan['changes']['parent_id'], 'bellhaven')

    def test_invalid_billing_blocks_ownership_plan(self):
        for value in (None, 'unknown', 'NaN', '-1', True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                plan_update(self.location, dict(self.account, outstanding_ar=value), 'bellhaven')

    def test_historical_account_does_not_match(self):
        result = classify(self.location, [dict(self.account, cow_current_account='new'), dict(self.account, id='new')])
        self.assertEqual(result['account_id'], 'new')

    def test_self_duplicate_is_blocked(self):
        with self.assertRaises(ValueError):
            plan_duplicate(self.account, self.account)


if __name__ == '__main__':
    unittest.main()
