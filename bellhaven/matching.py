"""Pure matching logic. No network access or CRM writes.

Name similarity alone never authorizes a match. Address and geography provide
independent evidence; co-located facilities and close runners-up require review.
"""
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
import re
import unicodedata


def normalize(value):
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.findall(r'[a-z0-9]+', text))


def address_key(value):
    aliases = {'street': 'st', 'road': 'rd', 'avenue': 'ave', 'boulevard': 'blvd',
               'drive': 'dr', 'lane': 'ln', 'pike': 'pk', 'northwest': 'nw', 'northeast': 'ne',
               'southwest': 'sw', 'southeast': 'se', 'north': 'n', 'south': 's',
               'east': 'e', 'west': 'w', 'suite': 'ste'}
    text = normalize(value)
    for words, short in (('north west', 'nw'), ('north east', 'ne'), ('south west', 'sw'), ('south east', 'se')):
        text = text.replace(words, short)
    return ' '.join(aliases.get(word, word) for word in text.split())


@dataclass(frozen=True)
class Candidate:
    account_id: str
    score: float
    evidence: tuple[str, ...]
    strong_address: bool
    strong_phone: bool


def rank_candidates(location, accounts):
    candidates = []
    for account in accounts:
        if account.get('duplicate_of_account') or account.get('cow_current_account'):
            continue  # historical records must not displace their successor
        evidence = []
        score = 0
        street = address_key(location.get('address'))
        exact_address = bool(street) and street == address_key(account.get('address'))
        same_state = bool(normalize(location.get('state'))) and normalize(location.get('state')) == normalize(account.get('state'))
        same_city = bool(normalize(location.get('city'))) and normalize(location.get('city')) == normalize(account.get('city'))
        zip_code = str(location.get('zip') or '')[:5]
        same_zip = bool(zip_code) and zip_code == str(account.get('zip') or '')[:5]
        if exact_address:
            score += 55
            evidence.append('Street address matches after abbreviation normalization')
        if same_city:
            score += 10
            evidence.append('City matches')
        if same_state:
            score += 10
            evidence.append('State matches')
        elif account.get('state') and location.get('state'):
            score -= 50
            evidence.append('State conflicts')
        if same_zip:
            score += 10
            evidence.append('ZIP matches')
        name = normalize(location.get('name'))
        similarity = SequenceMatcher(None, name, normalize(account.get('name'))).ratio() if name else 0
        score += 15 * similarity
        phone = re.sub(r'\D', '', str(location.get('phone') or ''))
        same_phone = bool(phone) and phone == re.sub(r'\D', '', str(account.get('phone') or ''))
        if same_phone:
            score += 20
            evidence.append('Phone matches')
        evidence.append(f'Name similarity: {similarity:.0%}')
        candidates.append(Candidate(str(account['id']), round(score, 2), tuple(evidence),
                                    exact_address and same_state and (same_city or same_zip),
                                    same_phone and similarity >= .9 and same_city and same_state))
    return sorted(candidates, key=lambda c: (-c.score, c.account_id))


def classify(location, accounts):
    ranked = rank_candidates(location, accounts)
    if not ranked or ranked[0].score < 40:
        return {'classification': 'missing', 'candidates': [asdict(c) for c in ranked[:3]]}
    best = ranked[0]
    unambiguous = len(ranked) == 1 or best.score - ranked[1].score >= 12
    confident = (best.strong_address and best.score >= 80 or best.strong_phone and best.score >= 60) and unambiguous
    return {'classification': 'matched' if confident else 'ambiguous',
            'account_id': best.account_id if confident else None,
            'candidates': [asdict(c) for c in ranked[:3]]}
