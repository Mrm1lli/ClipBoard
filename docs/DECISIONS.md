# Implementation decisions and limits

- Python + Flask + SQLite minimize moving parts for a small local review workflow.
- Deterministic matching keeps evidence explainable; there are no runtime LLM calls.
- Full snapshots are local and ignored by Git. Proposal evidence includes source
  URLs and field values; snapshots additionally retain collection time and HTML hash.
- The homepage includes a community omitted from the directory. Discovery takes
  their union and checks the advertised count before drawing absence conclusions.
- The API uses `chow_current_account`, although some task wording calls it COW.
  A tested adapter maps the internal name to the observed API field.
- Address spelling/abbreviation changes are proposed even when semantically equal;
  reviewers may reject such cosmetic changes. Matching itself normalizes them.
- The UI requires explicit approval of a concrete plan, including a specific
  duplicate survivor. It escapes source content and validates session tokens.
- Approved and Applied are distinct states. Exceptions leave a visible Applying
  entry with a generic safe error; no sensitive response bodies are displayed.
- API bodies are not documented in OpenAPI. Account field names were inspected
  read-only, then live POST/PATCH behavior was confirmed through candidate-approved
  writes and independent CRM reads. Protected ownership transfer verification remains
  outstanding until those plans are approved.
- Creates carry exact operation markers in `note` to recover after lost responses.
  This depends on the API preserving notes. Read-back checks detect incompatibility.
- No remote conditional writes/transactions are documented. Local locks and baseline
  checks cannot prevent every external race. Multi-step failures are visible and
  recoverable, not claimed atomic.
- The review UI is local only. Deployment, shared authentication, telemetry, and
  production scheduling infrastructure are outside this exercise's scope.
