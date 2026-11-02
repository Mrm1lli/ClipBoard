"""Persistent proposal decisions and resumable operation journal.

A proposal key includes its exact intended mutation and relevant CRM baseline.
Identical observations keep their decision. Changed evidence creates a new review.
"""
import hashlib
import json
from pathlib import Path
import sqlite3


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


class Store:
    def __init__(self, path='data/review.sqlite3'):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending',
                decision_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                decided_at TEXT
            );
            CREATE TABLE IF NOT EXISTS operations (
                proposal_id TEXT NOT NULL REFERENCES proposals(id),
                step TEXT NOT NULL, result TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(proposal_id, step)
            );
        ''')
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(proposals)')}
        for name, declaration in [('selected_choice', 'INTEGER'), ('execution_error', "TEXT NOT NULL DEFAULT ''")]:
            if name not in columns:
                self.db.execute(f'ALTER TABLE proposals ADD COLUMN {name} {declaration}')
        self.db.commit()

    def close(self):
        self.db.close()

    def propose(self, payload):
        encoded = canonical(payload)
        key = hashlib.sha256(encoded.encode()).hexdigest()
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO proposals(id, payload) VALUES (?, ?)', (key, encoded))
        return key

    def get(self, key):
        row = self.db.execute('SELECT * FROM proposals WHERE id=?', (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        result = dict(row)
        result['payload'] = json.loads(result['payload'])
        return result

    def list(self):
        return [self.get(row[0]) for row in self.db.execute('SELECT id FROM proposals ORDER BY created_at, id')]

    def decide(self, key, decision, note='', choice=None):
        if decision not in ('approved', 'rejected'):
            raise ValueError('Decision must be approved or rejected')
        payload = self.get(key)['payload']
        if decision == 'approved' and 'choices' in payload:
            if choice is None or not 0 <= choice < len(payload['choices']):
                raise ValueError('Choose a valid reviewed survivor/plan before approval')
        with self.db:
            cursor = self.db.execute('''UPDATE proposals SET state=?, decision_note=?, selected_choice=?, decided_at=CURRENT_TIMESTAMP
                WHERE id=? AND state='pending' ''', (decision, note, choice, key))
            if cursor.rowcount != 1:
                raise ValueError('Proposal is missing or has already been decided')

    def claim(self, key):
        """Only one worker may begin executing an approved proposal."""
        with self.db:
            cursor = self.db.execute("UPDATE proposals SET state='applying' WHERE id=? AND state='approved'", (key,))
            if cursor.rowcount != 1:
                raise ValueError('Proposal must be approved and not already applying/applied')

    def record_step(self, key, step, result):
        with self.db:
            if self.get(key)['state'] != 'applying':
                raise ValueError('Cannot journal an operation without an approved execution claim')
            self.db.execute('INSERT INTO operations(proposal_id, step, result) VALUES (?, ?, ?)',
                            (key, step, canonical(result)))

    def step_result(self, key, step):
        row = self.db.execute('SELECT result FROM operations WHERE proposal_id=? AND step=?', (key, step)).fetchone()
        return json.loads(row[0]) if row else None

    def finish(self, key):
        with self.db:
            cursor = self.db.execute("UPDATE proposals SET state='applied' WHERE id=? AND state='applying'", (key,))
            if cursor.rowcount != 1:
                raise ValueError('Proposal must be applying')
