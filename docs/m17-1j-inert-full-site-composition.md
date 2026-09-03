# M17.1J inert full-site application composition

M17.1J extends the existing source-only Marketplace application composition by wiring the reviewed M17.1I same-origin site host into the same inert state -> API -> HTTP object graph.

The composition accepts **caller-injected static bytes** for `index_html`, `app_js`, and `styles_css`. It passes those exact bytes to `MarketplaceSiteHostAdapter` and passes the exact `MarketplaceApplicationHttpAdapter` instance as the site host's application HTTP dependency. No second product API or alternate business model is introduced.

Composition remains inert. Calling `compose_marketplace_application(...)` constructs Python objects only. Storage initialization still happens only through the existing explicit `MarketplaceApplicationComposition.initialize()` call.

## Authority boundary

This slice adds **no live PostgreSQL connection**, provider selection, migration execution, database provisioning, credentials, or administration.

It adds **no HTTP listener/server activation**, socket bind/listen/accept, TLS, host/port ownership, public traffic, process/service lifecycle, configuration loading, environment/secret discovery, or deployment behavior.

It adds **no runtime filesystem asset loading** or path traversal. Static content enters only through caller-injected exact bytes and remains subject to the reviewed M17.1I response bounds.

It adds no Android dependency resolution/build/runtime, signing, installation, distribution, service restart, configuration change, production deployment, or other runtime mutation.

A future executable host may choose how to obtain reviewed static bytes, create a PostgreSQL connection factory, and select a network server. Each of those is a separate runtime capability requiring its own review and authorization.
