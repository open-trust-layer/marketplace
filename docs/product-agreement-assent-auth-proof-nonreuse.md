# Agreement assent authentication-proof non-reuse

## Product invariant

Marketplace authentication proves possession for an authentication challenge.
Agreement assent proves one party's assertion over one exact Agreement
candidate. These are different signed messages and different product
semantics.

A `MarketplaceAuthenticationProof` must therefore never be relabelled,
converted, or accepted as Agreement assent evidence.

## Frozen boundary

The contract tests require three independent barriers:

1. the Agreement proof service accepts only exact
   `AgreementAssentSigningPreparation` during finalization, so an
   authentication proof is rejected before Agreement proof construction;
2. Agreement coordination accepts only exact `VerifiedAgreementAssent`, so
   an authentication proof cannot reach the evidence preparer or store;
3. the complete Python `agreement_assent*.py` application/reference stack
   has no dependency on the authentication-proof profile or its transcript,
   parser, or proof constructor.

The browser authentication and Agreement signing capabilities may coexist in
the reviewed authenticated bootstrap, but coexistence is not proof conversion.

## Boundary

This slice adds tests and documentation only. It does not generate/import keys,
sign authentication or Agreement material, initialize persistent coordination,
connect to PostgreSQL, execute localhost/runtime code, publish an Agreement,
deploy, or administer provider settings.
