# M17.7U — Explicit local evidence JSON export

Profile: `MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_EXPORT_V1`

Issue: #508.

## Purpose

M17.7T prepares the exact non-secret authenticated local-flight evidence JSON in
memory. M17.7U adds one separate, explicit browser action that downloads only
that already-prepared reviewed object as a local JSON file for offline M17.7R
validation.

The export is not automatic and is unavailable until a current prepared evidence
document exists.

## Exact export contract

The selected page adds one explicit **Download evidence JSON** button.

The button remains disabled until the current prepared evidence object still
matches all current evaluator and lifecycle observations:

- exact merged main commit;
- positive CI run number;
- exact `127.0.0.1` origin;
- explicit buyer-authentication observation;
- current listing, Proposal, acceptance, Agreement, publication, and completion
  identities/results;
- exact reviewed false truth/payment/network/deployment boundaries.

If any of those values become stale before export, the prepared document is
cleared and no file action occurs.

## Local file shape

The explicit export serializes the already-reviewed in-memory object with
`JSON.stringify(..., null, 2)`, appends one trailing newline, and downloads it
with the stable filename:

`marketplace-authenticated-local-flight-evidence.json`

The browser Blob content type is
`application/json;charset=utf-8`. No value is reconstructed from rendered
HTML text.

The resulting file is intended for:

`python tools/marketplace_authenticated_local_flight_evidence.py marketplace-authenticated-local-flight-evidence.json`

## Transient browser resources

The file action creates one transient object URL only after the explicit button
click. The temporary anchor is removed and the object URL is revoked in a
`finally` block immediately after the click attempt.

No object URL, evidence document, or file handle is retained by a storage API.

## Boundary

M17.7U adds only an explicit local browser download of the already-reviewed
non-secret evidence object.

It adds no automatic download, clipboard action, upload, fetch, WebSocket,
EventSource, localStorage, sessionStorage, IndexedDB, service worker, background
timer, server route, database access, browser automation, signing authority,
public networking, deployment, payment, settlement, production credential, or
universal-truth authority.

Downloading the file is not itself live-flight acceptance. Acceptance still
requires the separately authorized real post-P loopback browser flight and a
successful offline M17.7R validation of the resulting exact file.

## Rollback

Source-only rollback: revert the M17.7U merge.
