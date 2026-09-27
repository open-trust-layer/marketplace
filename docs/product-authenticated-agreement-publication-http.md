# Authenticated Agreement publication HTTP

This slice exposes the smallest reviewed HTTP composition for publishing one already-formed Agreement.

## Route

`POST /api/agreements/{proposal_record_id}`

The JSON body is exact and contains only:

```json
{"acceptance_record_id":"<exact immutable Proposal-acceptance Record Identity>"}
```

There is no ambient or "latest acceptance" selection.

## Authority flow

The adapter:

1. requires the existing authenticated session;
2. derives the actor only from that session;
3. resolves the exact Proposal and explicit acceptance identity through the reviewed Agreement-assent candidate resolver;
4. re-evaluates retained verified assent through the reviewed Agreement-assent workflow;
5. runs the reviewed Agreement publication preflight;
6. requires `EVIDENCE_SUFFICIENT_FOR_PROFILE`, actor membership, and actor assent coverage;
7. touches the same session only after all read-only checks are canonical-positive;
8. calls the reviewed Agreement publication service exactly once;
9. returns only Agreement Record Identity, store disposition, and change sequence.

No signing occurs in this route.

## Fail-closed boundary

Malformed requests, caller-supplied principal/public-key/trust/attribution fields, missing exact acceptance identity, candidate resolution failure, incomplete formation, non-party actors, uncovered actor assent, noncanonical preflight, invalid session, and publication-service failure do not create an Agreement through this adapter.

The adapter does not add another trust source. Retained proof material becomes formation evidence only through the already-reviewed Agreement assent formation service and verification-method snapshot.

## Non-goals

This source slice does not activate a runtime route, bind a socket, migrate PostgreSQL, choose production configuration, create or export keys, sign in the browser, perform payment/settlement/fulfillment, deploy a service, or authorize any public-network action.

Runtime wiring remains a separate reviewed step after this HTTP/application composition is merged green.
