"""Loopback review app. Approval is explicit and immediately executes its plan."""
import os
import secrets
from flask import Flask, abort, redirect, render_template, request, session, url_for
from .store import Store
from .executor import apply


def create_app(database='data/review.sqlite3', execute=apply):
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.config.update(SESSION_COOKIE_SAMESITE='Strict', MAX_CONTENT_LENGTH=16384,
                      TRUSTED_HOSTS=['127.0.0.1', 'localhost'])

    @app.before_request
    def protect_decisions():
        if request.method == 'POST':
            expected = session.get('csrf')
            supplied = request.form.get('csrf', '')
            if not expected or not secrets.compare_digest(expected, supplied):
                abort(400, 'Invalid review session. Reload the page.')

    @app.get('/')
    def index():
        session.setdefault('csrf', secrets.token_hex(32))
        store = Store(database)
        try:
            proposals = store.list()
        finally:
            store.close()
        state = request.args.get('state', 'pending')
        visible = [p for p in proposals if state == 'all' or p['state'] == state]
        return render_template('review.html', proposals=visible, all_proposals=proposals,
                               current_state=state, csrf=session['csrf'])

    @app.post('/proposals/<key>/decision')
    def decide(key):
        decision = request.form.get('decision')
        store = Store(database)
        try:
            raw_choice = request.form.get('choice')
            choice = int(raw_choice) if raw_choice is not None else None
            store.decide(key, decision, request.form.get('note', '').strip(), choice)
        except (ValueError, KeyError) as exc:
            abort(409, str(exc))
        finally:
            store.close()
        if decision == 'approved':
            try:
                execute(database, key)
            except Exception:
                # Raw API exceptions can contain sensitive details; show the saved safe status.
                store = Store(database)
                try:
                    state = store.get(key)['state']
                    if state == 'approved':
                        with store.db:
                            store.db.execute("UPDATE proposals SET execution_error='Approved but not started. Another workflow may be running; investigate and retry this approved plan.' WHERE id=?", (key,))
                finally:
                    store.close()
                return redirect(url_for('index', state=state))
        return redirect(url_for('index', state='applied' if decision == 'approved' else 'rejected'))

    return app


if __name__ == '__main__':
    create_app(os.environ.get('BELLHAVEN_DB', 'data/review.sqlite3')).run(host='127.0.0.1', port=5000, debug=False)
