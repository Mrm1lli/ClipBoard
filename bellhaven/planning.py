"""Describe mutations for review; never execute them here."""
from decimal import Decimal, InvalidOperation

FACILITY_FIELDS = ('name', 'address', 'city', 'state', 'zip', 'care_offerings')


def money(value):
    # Fail closed on missing/invalid billing information before ownership changes.
    if value is None or isinstance(value, bool):
        raise ValueError('Billing values must be present and numeric')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Invalid billing value') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Billing values must be finite and nonnegative')
    return result


def plan_update(location, account, parent_id):
    """Return a reviewable plan using a canonical internal field vocabulary.

    The API adapter must translate fields only after its live schema is verified.
    A change-of-ownership plan leaves all old fields intact except its required
    successor link; no billing amounts are copied to the new facility account.
    """
    desired = {key: location[key] for key in FACILITY_FIELDS if key in location}
    desired['status'] = 'Active'
    moving = str(account.get('parent_id')) != str(parent_id)
    if moving:
        protected = money(account.get('lifetime_revenue')) > 0 and money(account.get('outstanding_ar')) > 0
        if protected:
            return {'kind': 'change_of_ownership', 'account_id': account['id'],
                    'before': dict(account), 'create': dict(desired, parent_id=parent_id),
                    'link_old_field': 'cow_current_account',
                    'reason': 'Revenue history and outstanding AR require preserving the old parent and billing account.'}
        desired['parent_id'] = parent_id
    changes = {key: value for key, value in desired.items() if account.get(key) != value}
    return {'kind': 'update' if changes else 'no_change', 'account_id': account['id'],
            'before': dict(account), 'changes': changes}


def plan_duplicate(loser, survivor):
    if str(loser['id']) == str(survivor['id']):
        raise ValueError('An account cannot duplicate itself')
    return {'kind': 'duplicate', 'account_id': loser['id'], 'before': dict(loser),
            'changes': {'status': 'Inactive', 'duplicate_of_account': survivor['id']},
            'reason': 'Reviewer must verify that both records represent the same facility.'}


def plan_absent(account):
    return {'kind': 'absent_from_website', 'account_id': account['id'], 'before': dict(account),
            'changes': {'status': 'Needs Review'},
            'reason': 'Not listed in the complete website snapshot; absence alone does not prove closure or ownership transfer.'}
