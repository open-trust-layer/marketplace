# Product Agreement publication write

This slice adds the first transport-neutral application-state write for a formed
Agreement candidate.

Publication is allowed only when an exact
`AgreementPublicationPreflightResult` is canonical and positive. Before writing,
the service independently re-derives the candidate Record Identity and rechecks that
the preflight targets that exact Agreement, reports
`EVIDENCE_SUFFICIENT_FOR_PROFILE`, names the acting principal as an Agreement
party, and uses the canonical `PRECONDITIONS_SATISFIED` reason.

The service then publishes exactly the already-built immutable Agreement record
through the existing Marketplace application-state service.

## Authority boundary

This is a protected write in the application layer, but this slice does **not**
expose that write through authentication composition, HTTP, Web, Android, database
configuration, public network, service startup, or deployment.

It does not create keys or proofs, establish legal enforceability or universal truth,
perform payment/settlement/fulfillment, or authorize any downstream protected
operation.

A later slice must bind this write to an authenticated session and transport route
before it is reachable by a user-facing product.
