import unittest
from bellhaven.client import Client, api_fields, canonical_account


class ClientTests(unittest.TestCase):
    def client(self, pages):
        client = Client.__new__(Client)
        client.request = lambda method, path: pages.pop(0)
        return client

    def test_pagination_reads_all_accounts(self):
        c = self.client([{'page': 1, 'data': [{'account_id': 'a'}], 'total': 2},
                         {'page': 2, 'data': [{'account_id': 'b'}], 'total': 2}])
        self.assertEqual([a['id'] for a in c.accounts()], ['a', 'b'])

    def test_repeated_ids_and_changing_totals_block_snapshot(self):
        for second in ({'page': 2, 'data': [{'account_id': 'a'}], 'total': 2},
                       {'page': 2, 'data': [{'account_id': 'b'}], 'total': 3}):
            with self.subTest(second=second), self.assertRaises(RuntimeError):
                self.client([{'page': 1, 'data': [{'account_id': 'a'}], 'total': 2}, second]).accounts()

    def test_api_ownership_field_is_chow(self):
        self.assertEqual(api_fields({'cow_current_account': 'new'}), {'chow_current_account': 'new'})
        self.assertEqual(canonical_account({'chow_current_account': 'new'})['cow_current_account'], 'new')


if __name__ == '__main__':
    unittest.main()
