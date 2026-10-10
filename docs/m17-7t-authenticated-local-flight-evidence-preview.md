# M17.7T — Explicit authenticated local-flight evidence preview

Profile: MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_PREVIEW_V1

Issue: #506.

## Purpose

M17.7S provides a pure browser-side projection into the strict M17.7R evidence shape.
M17.7T selects that projector into the active Marketplace page as an explicit evaluator preview
after the reviewed Agreement-publication and fulfillment-completion state already exists.

The page does not infer a buyer session that it cannot observe. The current tab derives seller
authentication from the active in-memory seller session and exact parent listing. The evaluator
must separately attest that buyer authentication was observed during the same local flight.

## Explicit inputs

The evaluator supplies the exact merged 40-hex main commit, a positive successful CI run number,
and one explicit checkbox confirming separately observed buyer authentication.

The page derives seller authentication, listing Record Identity, Proposal Record Identity,
acceptance Record Identity, Agreement formation result, Agreement publication result, and
seller delivery completion result from current in-memory state.

The preview is enabled only on exact 127.0.0.1, after sufficient formation with no missing
parties and after both explicit Agreement publication and exact seller-attributed completion exist.

### M17.7AA — Two-party observation guard

The operator-facing preview and explicit export now additionally require that the
selected Proposal's **record-derived buyer principal differs from the parent
Listing's seller principal**. The already-observed Agreement formation result
must list **both exact principals** in its required and covered principals arrays.
Any missing, malformed or inconsistent arrays fail closed before evidence preparation;
the existing export currentness check re-evaluates the same guard.

This is a strict UI evidence-readiness requirement, not a change to Agreement formation,
server-side principal binding, authentication, persistence, or the offline JSON schema.
A manually checked buyer-authentication observation still does **not** prove that the
buyer logged in; the operator must observe that separate authenticated browser
session during the authorized flight. A source-only preview success is not evidence
of live acceptance.

## Output

The explicit Prepare non-secret evidence preview click dynamically selects M17.7S and renders its
exact JSON object in-page. That object is intended for offline validation with M17.7R.

The preview is cleared whenever the Agreement/publication/completion state or evaluator metadata
changes, preventing a stale document from remaining visible as if it represented the current flight.

## Boundary

M17.7T does not download, copy, persist, upload, or automatically submit the evidence. It adds no
file API, clipboard action, storage, background activity, new server route, browser automation,
database access, signing, public network, deployment, payment, settlement, or production authority.

Preparing the preview is not itself a live-flight acceptance claim. Final acceptance still requires
the separately authorized real post-P loopback flight and successful offline M17.7R validation of
the resulting non-secret document.

## Rollback

Source-only rollback: revert the M17.7T merge.
