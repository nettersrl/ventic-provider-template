# Contoso provider template

Inspect git status and preserve owner edits. Do not commit, push, publish or deploy
without explicit instructions. This fictional Contoso Ltd installation is a
template; it contains no Microsoft assets, credentials or owner legal terms.
Keep every installation choice here; consume only sources/artifacts pinned in
stack.lock.json. Never scan for sibling checkouts or float to branches.

Production requires netter-ai-platform licensed signed releases. Preserve payment
accounting, encryption keys, local PII, CSRF, unbuffered SSE, both installer leases,
operator schedules and reconciliation journals. Never run archived NI/VPS scripts.
Use private/ (0700; files 0600) for runtime inputs; exclude it from artifacts.
Use disposable Docker databases and named test clusters; never production fixtures.
UI is Italian with explicit English translations. Legal documents must be supplied
by the owner. Report actual Kubernetes, browser and payment checks precisely.

## Coordinated commit and push procedure

A user request to push Ventic stack work implicitly authorizes the necessary
prerequisite commits/pushes, reviewed submodule repins, generated contract updates,
frontend dependency artifact preparation/publication through its CI, and downstream
provider lock updates. Complete that dependency chain without asking again for each
repository. A commit-only request does not authorize pushes or publication.
This does not authorize deployment, Licman catalog publication, new
release tags, key replacement, unrelated repositories, or inclusion of private data.

Use `main` unless the user names another branch. Inspect each affected repository's
status, diff and origin; fetch `origin/main` and preserve owner edits. Integrate
upstream changes without force-pushing or discarding work. The order is:

1. Commit and push `ventic-common` first. Verify the exact commit is reachable from
   `origin/main` before updating consumers. Never pin an unpublished common commit.
2. In `ventic-frontend` and `ventic-backend`, fetch the common submodule's origin,
   check out that reviewed full commit detached, stage the gitlink and run
   `make common-sync`. Keep `../ventic-common.git` and recursive initialization;
   never use `submodule update --remote` during builds.
3. Check/version the frontend, commit and push it, then build its dependency bundle
   from that clean published commit. Preserve truthful commit/dirty provenance.
   Ordinary main-branch CI may publish the immutable dependency package; never
   fabricate a checksum, URL, commit or clean-state flag. Import the reviewed exact
   bundle into backend with `make frontend-import BUNDLE=... ARGS=--pin`.
4. Check, commit and push backend, including its common gitlink and frontend locks.
   In each affected provider, run `scripts/sources.py pin --backend-dir <explicit>
   --frontend-dir <explicit>` against those clean published checkouts. Preserve
   provider-specific paths and configuration, update chart dependency versions if
   needed, validate the lock and commit/push the provider on `main`.
5. Run the checks appropriate to changed files and report their actual results.
   Verify remote main SHAs, clean source trees, initialized common submodules at
   staged gitlinks and coherent provider/artifact pins. If CI or an artifact upload
   remains pending/unavailable, state that explicitly; never claim publication or
   deployment from a Git push alone. Private inputs, logs, dumps and build caches
   stay ignored. Keep published historical artifacts and legal sources immutable.
