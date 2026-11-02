# Recording tutorial and two-minute script

## Before recording

1. Follow README local setup and run the tests. Enter the token before recording.
2. Run `python -m bellhaven run` using your virtual environment's Python.
3. Start `python -m bellhaven serve` and open the local address printed by Flask.
4. Open two more browser tabs: the Bellhaven website and your assessment workspace's
   **CRM browser** link. Do not show the workspace token block in the recording.
5. Keep a few real proposals pending for the recording. Review the rest normally;
   do not clear the SQLite database to manufacture a fresh queue.
6. Useful real examples for the initial dataset:
   - **Lima:** change the wrong parent directly. Revenue exists but AR is zero.
   - **Marietta or Tiffin:** preserve the billing account; create a successor under
     Bellhaven because revenue and outstanding AR are both positive.
   - **Owosso:** duplicate records; website phone supports surviving account
     `001EGU7BMJ942ZTRE6`. Compare both records before approving.
   - **Kalamazoo:** proposed address change is only “Road” to “Rd.” If you judge this
     unnecessary, reject it with that explanation. This demonstrates a legitimate
     rejection without leaving an ownership error uncorrected.
7. Set up any screen recorder. Share the finished video so anyone with the link can
   view. A single browser window with the tabs above is sufficient.

These are review suggestions, not prior approvals. Recheck the actual queue;
changes already decided will no longer appear under Pending.

## Two-minute recording

| Time | On screen | Suggested narration |
|---|---|---|
| 0:00–0:15 | Review app, Pending tab | “This tool compares Bellhaven's public locations with our CRM sandbox. The daily job only proposes changes. Every CRM write requires an explicit review decision.” |
| 0:15–0:35 | Open Lima, source evidence and before/after table | “Here the website name and address identify the facility, but the CRM has the wrong parent. I can inspect the source, matching signals, and exact changes. Revenue exists, but outstanding AR is zero, so the SOP permits re-parenting this account directly.” |
| 0:35–0:50 | Add note, check acknowledgement, approve Lima | “I've reviewed the evidence and approve this plan. The app rechecks the original record, applies the changes, and reads it back. Applied means verification succeeded.” |
| 0:50–1:10 | Marietta or Tiffin, original billing fields and new-account plan | “This one has revenue history and unpaid AR. We preserve the old account and its parent, create the current facility under Bellhaven, and link the old account to its successor. We don't move billing history.” |
| 1:10–1:30 | Kalamazoo, reject with note | “Not every proposal deserves a write. This one only abbreviates Road to Rd; the existing address is already equivalent. I'll reject it. The decision persists, so tomorrow's identical run won't ask again.” |
| 1:30–1:50 | CRM browser, search Lima and inspect parent | “Here's the approved change in the CRM itself. The app's local decision history and the remote record are separate, and both show the outcome.” |
| 1:50–2:00 | Applied/Rejected tabs, optionally show rerun summary | “Repeated discovery keeps decisions and avoids duplicate proposals. I used AI to help implement and test the system, then checked its behavior against the actual website and sandbox.” |

Speak naturally and shorten as needed. Only say a write succeeded after Applied
appears and the CRM browser confirms it. If a write stops, investigate before
recording; don't narrate an expected result as if it happened.

## After recording

1. Review the remaining proposals and select survivors carefully for duplicate groups.
2. Resolve any Applying errors, then verify the resulting records in the CRM browser.
3. Run discovery again. Rejected identical proposals should stay rejected and applied
   corrections should not generate new pending work.
4. Confirm the recording link works without your login.
5. Update the writeup with actual results and time spent. Submit the code link, video
   link, honest time, and writeup before November 4, 2026 at 11:30 AM EST.

## Be ready for the live interview

Explain scraper completeness (the homepage-only Findlay listing), matching signals,
why names alone are insufficient, billing protection, duplicate survivor choices,
and persistent decisions. Be able to change a mapping or threshold in
`pipeline.py`/`matching.py`, run tests, and refresh discovery. Explain that HTTP API
writes cannot be made fully atomic without server support.
