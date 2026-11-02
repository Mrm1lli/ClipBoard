# Submission writeup draft

I built a Python/Flask/SQLite tool that scrapes Bellhaven's website, matches locations
to CRM accounts, and presents proposed changes with evidence for human approval.
The scraper traverses three directory pages and homepage-only community links;
this matters because Findlay is absent from the directory. Completeness checks
reconciled 35 website locations with a 121-account CRM snapshot.

Matching uses normalized addresses, geography, name similarity, and supporting
phone evidence. It keeps co-located records together for explicit survivor selection
rather than treating the top score as an automatic approval. Website care labels
are mapped to the CRM vocabulary. The initial queue contained 24 update proposals,
4 creates, 5 duplicate groups, 2 billing-protected ownership changes, and 3 absent
listings. Absence alone warrants Needs Review, not a claim that a facility closed.

For ownership changes with both lifetime revenue and outstanding AR, the plan
preserves the old account and parent, creates a successor under the correct parent,
and links the old account through the API's `chow_current_account`. Other ownership
changes re-parent the existing account. Duplicate losers become Inactive and link
to the chosen survivor; nothing is deleted or merged.

I used OpenAI Codex for implementation and test assistance, directed it with the
exercise requirements, and checked its work through tests and live read-only
inspection. SQLite retains decisions and operation receipts across daily runs.
Approval rechecks CRM state before writing and verifies the result afterward;
unique create markers support recovery after a lost response. A cron example runs
read-only proposal generation daily. No LLM calls or paid API keys are required.

**Complete before submission:** Describe the actual approvals/rejections, chosen
duplicate survivors, verified final CRM results, and any remaining uncertain
records. The current implementation has not yet performed a live approved write.
Record actual time spent separately; do not reuse an estimated target as actual time.

Next I would add server-supported conditional updates/idempotency, operational
alerts, stronger address parsing, and durable evidence versioning. Client-side
journaling cannot make multiple CRM API calls atomic or prevent all external races.
