"""Scrape every paginated directory entry and its detail page, failing closed."""
from datetime import datetime, timezone
import hashlib
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen
from bs4 import BeautifulSoup
from .client import BASE


def fetch(url):
    if urlsplit(url).netloc != urlsplit(BASE).netloc:
        raise ValueError('Website link leaves assessment host')
    with urlopen(url, timeout=30) as response:
        if urlsplit(response.url).netloc != urlsplit(BASE).netloc:
            raise ValueError('Unexpected website redirect')
        return response.read().decode('utf-8')


def parse_detail(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    fields = {dt.get_text(' ', strip=True): dt.find_next_sibling('dd') for dt in soup.select('dl.detail dt')}
    address = fields['Address'].get_text('\n', strip=True).splitlines()
    if len(address) != 2:
        raise ValueError(f'Unexpected address format: {url}')
    match = re.fullmatch(r'(.+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', address[1])
    if not match:
        raise ValueError(f'Unexpected city/state/ZIP: {url}')
    care = [node.get_text(' ', strip=True) for node in fields['Care Offerings'].select('.badge')]
    if not care or not soup.h1:
        raise ValueError(f'Missing required detail fields: {url}')
    return {'name': soup.h1.get_text(' ', strip=True), 'address': address[0],
            'city': match[1], 'state': match[2], 'zip': match[3], 'care_offerings': care,
            'phone': fields['Phone'].get_text(' ', strip=True), 'source_url': url,
            'source_sha256': hashlib.sha256(html.encode()).hexdigest()}


def scrape(get=fetch):
    home = get(BASE + '/')
    count_match = re.search(r'serve\s+(\d+)\s+communities', home)
    if not count_match:
        raise ValueError('Cannot establish advertised community count')
    expected = int(count_match[1])
    pending = [BASE + '/communities']
    seen = set()
    detail_urls = {urljoin(BASE, a['href']) for a in BeautifulSoup(home, 'html.parser').select('a[href]')
                   if urlsplit(urljoin(BASE, a['href'])).path.startswith('/communities/')}
    advertised_pages = set()
    while pending:
        url = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if len(seen) > 100:
            raise ValueError('Unexpected directory pagination size')
        soup = BeautifulSoup(get(url), 'html.parser')
        page = re.search(r'Page\s+(\d+)\s*/\s*(\d+)', soup.get_text(' ', strip=True))
        if not page:
            raise ValueError('Missing directory pagination metadata')
        advertised_pages.add((int(page[1]), int(page[2])))
        links = soup.select('.card h3 a[href]')
        if not links:
            raise ValueError('Directory returned no community links')
        detail_urls.update(urljoin(BASE, a['href']) for a in links)
        for a in soup.select('.pager a[href]'):
            target = urljoin(BASE, a['href'])
            if urlsplit(target).path != '/communities':
                raise ValueError('Unexpected pagination link')
            if target not in seen:
                pending.append(target)
    totals = {total for _, total in advertised_pages}
    if len(totals) != 1 or {page for page, _ in advertised_pages} != set(range(1, next(iter(totals)) + 1)):
        raise ValueError('Incomplete directory pagination')
    if len(detail_urls) != expected:
        raise ValueError(f'Directory has {len(detail_urls)} locations; homepage advertises {expected}')
    locations = [parse_detail(get(url), url) for url in sorted(detail_urls)]
    return {'collected_at': datetime.now(timezone.utc).isoformat(), 'directory_pages': len(advertised_pages),
            'expected_count': expected, 'locations': locations}
