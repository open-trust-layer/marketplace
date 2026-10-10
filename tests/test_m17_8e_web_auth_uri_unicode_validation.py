"""M17.8E: active Web auth identifiers are valid Unicode scalar sequences."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "web" / "auth_establishment.js",
    ROOT / "web" / "auth_ed25519_proof_provider.js",
)
DOC = ROOT / "docs" / "m17-8e-web-auth-uri-unicode-validation.md"


class M178EWebAuthUriUnicodeTests(unittest.TestCase):
    def test_every_entrypoint_rejects_malformed_scalar_sequences_before_utf8(self):
        for file in FILES:
            with self.subTest(file=file.name):
                text = file.read_text(encoding="utf-8")
                start = text.index("function reviewedUri(value)")
                end = text.index("function ", start + 10)
                guard = text[start:end]
                self.assertIn("!validUnicodeScalarSequence(value)", guard)
                size = "utf8Bytes(value)" if file.name != "auth_ed25519_proof_provider.js" else "utf8(value).length"
                self.assertIn(size, guard)
                self.assertLess(guard.index("!validUnicodeScalarSequence(value)"),
                                guard.index(size))
                self.assertIn("throw stable", guard)
                self.assertIn("return value;", guard)

    def test_each_scalar_guard_rejects_unpaired_high_and_low_code_units(self):
        for file in FILES:
            with self.subTest(file=file.name):
                text = file.read_text(encoding="utf-8")
                start = text.index("function validUnicodeScalarSequence(value)")
                end = text.index("function reviewedUri(value)", start)
                guard = text[start:end]
                for token in (
                    "index < value.length",
                    "value.charCodeAt(index)",
                    "unit >= 0xd800 && unit <= 0xdbff",
                    "value.charCodeAt(index + 1)",
                    "next >= 0xdc00 && next <= 0xdfff",
                    "unit >= 0xdc00 && unit <= 0xdfff",
                    "index += 1;",
                    "return false;",
                    "return true;",
                ):
                    self.assertIn(token, guard)
                for forbidden in ("normalize(", "replace(", "fetch(", "sign(", "window",
                                  "TextDecoder", "String.fromCharCode("):
                    self.assertNotIn(forbidden, guard)

    def test_validation_precedes_any_external_auth_or_signature_operation(self):
        bootstrap = FILES[0].read_text(encoding="utf-8")
        establishment = FILES[1].read_text(encoding="utf-8")
        proof = FILES[2].read_text(encoding="utf-8")
        bootstrap_flow = bootstrap[bootstrap.index("async function establishSession("):
                                   bootstrap.index("function structuredAuthoringClient(")]
        self.assertLess(bootstrap_flow.index("reviewedUri(principalValue)"),
                        bootstrap_flow.index("createMarketplaceWebAuthEd25519ProofProvider("))
        self.assertLess(bootstrap_flow.index("reviewedUri(verificationMethodValue)"),
                        bootstrap_flow.index("createMarketplaceWebAuthEstablishment("))
        establishment_flow = establishment[establishment.index("async function establishSession("):
                                         establishment.index("return Object.freeze({ establishSession });")]
        self.assertLess(establishment_flow.index("reviewedUri(principalValue)"),
                        establishment_flow.index("await postJson("))
        self.assertLess(establishment_flow.index("reviewedUri(verificationMethodValue)"),
                        establishment_flow.index("await postJson("))
        proof_init = proof[proof.index("function createMarketplaceWebAuthEd25519ProofProvider("):
                           proof.index("async function createAuthenticationProof(")]
        self.assertIn("const pinnedVerificationMethod = reviewedUri(verificationMethod);", proof_init)
        proof_request = proof[proof.index("function reviewedRequest("):
                             proof.index("function encodeSignature(")]
        self.assertIn("reviewedUri(request.principal);", proof_request)
        self.assertIn("reviewedUri(request.verificationMethod);", proof_request)

    def test_all_profile_and_proof_constants_remain(self):
        proof = FILES[2].read_text(encoding="utf-8")
        establishment = FILES[1].read_text(encoding="utf-8")
        bootstrap = FILES[0].read_text(encoding="utf-8")
        self.assertIn('"MARKETPLACE_WEB_AUTH_ED25519_PROOF_PROVIDER_V1"', proof)
        self.assertIn('"MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1"', establishment)
        self.assertIn('"AUTH_PROOF_UNAVAILABLE"', proof)
        self.assertIn('"AUTH_REQUEST_INVALID"', establishment)
        self.assertIn('"AUTH_REQUEST_INVALID"', bootstrap)
        self.assertIn("Uint8Array", proof)
        self.assertIn("privateKey", proof)
        self.assertIn("session.adoptEstablishedSession(", establishment)

    def test_document_and_source_scope(self):
        document = DOC.read_text(encoding="utf-8")
        for token in ("MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1",
                      "unpaired surrogate", "no network", "source-only rollback",
                      "no signature", "before"):
            self.assertIn(token, document)


if __name__ == "__main__":
    unittest.main()
