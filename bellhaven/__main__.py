import argparse
import json
import os
from .pipeline import run
from .executor import apply, workflow_lock


def main():
    parser = argparse.ArgumentParser(description='Bellhaven: discover daily, review explicitly, verify writes.')
    parser.add_argument('--database', default=os.environ.get('BELLHAVEN_DB', 'data/review.sqlite3'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('run', help='Read-only discovery and proposal generation; never writes to CRM')
    sub.add_parser('serve', help='Start local approval/rejection app')
    retry = sub.add_parser('retry', help='Resume an already approved proposal after investigating its journal')
    retry.add_argument('proposal_id')
    args = parser.parse_args()
    if args.command == 'run':
        with workflow_lock(args.database):
            print(json.dumps(run(args.database), indent=2))
    elif args.command == 'retry':
        apply(args.database, args.proposal_id)
        print('Approved proposal applied and verified.')
    else:
        from .web import create_app
        create_app(args.database).run(host='127.0.0.1', port=5000, debug=False)


if __name__ == '__main__':
    main()
