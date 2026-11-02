# Bellhaven CRM reconciliation

A local, human-reviewed reconciliation tool for the Bellhaven take-home exercise.
Python + Flask + SQLite; no paid services or LLM API calls.

## Status

Live discovery verified: **35 website locations**, **121 CRM accounts**, **38 review
proposals** (24 updates, 4 creates, 5 duplicate groups, 2 protected ownership changes,
3 accounts absent from the website). Repeating discovery did not grow the queue.

The app executes approved plans and verifies each write with a fresh GET. Execution
has been tested against a simulated CRM, including lost responses and restart
recovery. Live CRM reads independently confirmed six updated accounts and one newly
created account after candidate review. Both live PATCH and POST paths have therefore
been exercised. Protected ownership transfers and the remaining reconciliation
still require review and verification. The API OpenAPI document omits request-body
schemas; the adapter uses observed field names with explicit read-back checks.

The cloud's network and secret settings work. Environment snapshot publication
failed in the product UI; publication is separate from running this application.

## Run locally

Python 3.12 is the tested version. On macOS/Linux, from this checkout:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
# Enter the token without echoing it or adding it to shell history:
read -r -s -p 'CRM token: ' BELLHAVEN_API_TOKEN; echo
export BELLHAVEN_API_TOKEN
.venv/bin/python -m bellhaven run
.venv/bin/python -m bellhaven serve
```

Open the local address printed by Flask in your own browser (port 5000). Keep the
terminal running. Use a second terminal for additional discovery commands.

Windows PowerShell equivalents (provided for portability; Windows has not been tested in this Linux environment):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$token = Read-Host 'CRM token' -AsSecureString
$env:BELLHAVEN_API_TOKEN = [System.Net.NetworkCredential]::new('', $token).Password
.\.venv\Scripts\python.exe -m bellhaven run
.\.venv\Scripts\python.exe -m bellhaven serve
```

Do not expose the token in a recording. The cloud already injects
`BELLHAVEN_API_TOKEN`, so cloud commands do not need a token entry step.

## Review workflow

1. `run` reads the website and all CRM pages, saves snapshots in `data/runs/`, and
   generates proposals. It never writes to the CRM.
2. On the Pending tab, open the source page and compare the current/proposed values.
   Address/name scores are evidence, not calibrated probabilities.
3. For duplicates, compare every survivor option. Exactly one account survives;
   the selected option explicitly shows which other accounts become Inactive.
4. Add a note, check the acknowledgement, and choose **Approve and apply this plan**.
   This immediately writes only that reviewed plan to your isolated CRM.
5. Rejection changes only local decision history. Identical proposals stay rejected.
6. Check Applied and verify the record in the assessment's read-only CRM browser.
7. If a plan stops partway through, it appears under Applying with an error message.
   A lock conflict can leave an Approved plan that has not started. Investigate the
   record/journal before using the explicit retry command below.
8. Repeat `run`. Completed corrections disappear from the pending queue. Decisions
   survive restarts; materially changed evidence or CRM baselines require new review.

```sh
.venv/bin/python -m bellhaven retry FULL_PROPOSAL_ID
```

The app is a loopback development tool, not a hosted multi-user service. Sessions
restart with the server; decisions remain in SQLite. `BELLHAVEN_DB` or the CLI's
`--database PATH` selects another database. Keep the database across daily runs.

## Matching and completeness

- Traverse all three directory pages **and homepage community links**. Findlay is
  homepage-only, so scraping the directory alone silently misses a location.
- Require the unique location count to match the homepage's advertised 35. Missing
  pages or unparsable detail fields stop discovery before absence proposals.
- Normalize punctuation, street abbreviations and directions, then compare street,
  city, state, ZIP, and names. Strong name + phone + geography can resolve a PO box.
- Address/geography agreement plus a clear score margin supports a single match.
  Co-located candidates are grouped for explicit survivor selection. A similar
  facility name at a conflicting address/state is not sufficient evidence.
- Map website “Memory Support” to CRM “Memory Care,” and “Short-Term Rehabilitation
  & Nursing” to “Skilled Nursing.” Preserve original labels in source evidence.
- Phone is supporting evidence; this exercise updates the requested location fields,
  not every discrepant phone number.

## Billing SOP and duplicate policy

A re-parenting plan checks both `lifetime_revenue` and `outstanding_ar`. When both
are positive, it creates the current facility under Bellhaven and changes only the
old account's ownership-successor link. It preserves the old parent, billing values,
and other old fields. Otherwise, it re-parents the existing record directly.
Missing/invalid financial values block planning. Internally the field is named
`cow_current_account`; the API adapter maps it to the actual `chow_current_account`.

Duplicates are marked Inactive and linked through `duplicate_of_account`. Survivor
recommendations favor matching phone, financial history, existing Bellhaven parent,
and name; they are not automatic approvals. Kettering is especially ambiguous:
three zero-balance records share the same address. The reviewer must explain the
chosen survivor. No accounts are merged or deleted.

An absent listing becomes Needs Review with an explanatory note; it is not detached
or declared closed based on absence alone. This preserves the billing relationship
for Sandusky while ownership is investigated.

## Daily schedule and safe reruns

[docs/crontab.example](docs/crontab.example) contains the daily schedule. Replace
its checkout path before installing it; the cron host's timezone determines 07:00.
`scripts/daily.sh` works from any directory and only generates proposals. For local
cron authentication, supply a private ignored `.env` file (`chmod 600 .env`) with
`BELLHAVEN_API_TOKEN=...`; the wrapper loads it. Do not commit it. For interactive
`serve`, export the token in its shell as shown above.

SQLite stores proposal fingerprints, decisions, selected plans, execution claims,
and an operation journal. Timestamps and source HTML hashes are retained in run
snapshots, not decision fingerprints. Pending plans superseded by new evidence are
archived. Approved plans recheck CRM baselines before writing. A local file lock
serializes discovery and execution. A create's unique note marker lets recovery
find a record when the server succeeded but the response was lost.

The remote API has no documented transactions, conditional PATCH, or native
idempotency keys. Re-reads and journals reduce risk but cannot eliminate races with
external CRM users or make multi-account writes atomic. Interrupted plans remain
visible and require investigation/retry; writes are never blindly retried.

## Validation and submission

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m bellhaven run
.venv/bin/python -m bellhaven run
```

Tests cover pagination, scraper completeness, matching ambiguity, billing rules,
rejection persistence, stale-data checks, approval gating, lost-create/patch-response
recovery, and the approval-to-CRM-to-rerun flow with a fake CRM.

[Final review checklist](docs/FINAL_REVIEW.md) prioritizes substantive corrections
remaining after the recording.
[Demo walkthrough and narration](docs/DEMO.md) explains what to present.
[Submission writeup draft](docs/WRITEUP.md) must be updated with actual review results
and honest time spent. The exercise is not finished until you apply your reviewed
corrections, verify the CRM, record the demo, and submit the links. No deployment or
environment publication is required to run locally.
