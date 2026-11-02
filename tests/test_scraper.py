import unittest
from bellhaven.client import BASE
from bellhaven.scraper import scrape

DETAIL = '''<h1>Bellhaven Test</h1><dl class="detail">
<dt>Address</dt><dd>123 Main St<br>Somewhere, OH 12345</dd>
<dt>Care Offerings</dt><dd><span class="badge">Assisted Living</span></dd>
<dt>Phone</dt><dd>(123) 456-7890</dd></dl>'''


class ScraperTests(unittest.TestCase):
    def pages(self):
        return {BASE + '/': 'We serve 3 communities <a href="/communities/new">New</a>',
                BASE + '/communities': '<div class="card"><h3><a href="/communities/one">One</a></h3></div><div class="pager">Page 1 / 2<a href="/communities?page=2">Next</a></div>',
                BASE + '/communities?page=2': '<div class="card"><h3><a href="/communities/two">Two</a></h3></div><div class="pager">Page 2 / 2</div>',
                **{BASE + '/communities/' + slug: DETAIL for slug in ('one', 'two', 'new')}}

    def test_pagination_and_homepage_only_location(self):
        result = scrape(self.pages().__getitem__)
        self.assertEqual(len(result['locations']), 3)
        self.assertEqual(result['directory_pages'], 2)
        self.assertIn(BASE + '/communities/new', [l['source_url'] for l in result['locations']])
        self.assertEqual(result['locations'][0]['zip'], '12345')

    def test_incomplete_directory_blocks_absence_inference(self):
        pages = self.pages()
        pages[BASE + '/'] = 'We serve 4 communities'
        with self.assertRaises(ValueError):
            scrape(pages.__getitem__)

    def test_incomplete_pagination_fails(self):
        pages = self.pages()
        pages[BASE + '/communities'] = pages[BASE + '/communities'].replace('<a href="/communities?page=2">Next</a>', '')
        with self.assertRaises(ValueError):
            scrape(pages.__getitem__)


if __name__ == '__main__':
    unittest.main()
