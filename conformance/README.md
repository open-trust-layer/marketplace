# Marketplace Conformance Vectors

Milestone 3 provides executable Marketplace Record Representation v1 vectors in `vectors/record-representation-v1.json`.

The vectors are generated and validated against the Open Layer Protocol reference implementation. The committed file records the exact OLP source commit used for identity derivation.

From a checkout of both repositories, with the OLP reference implementation installed or on `PYTHONPATH`:

```text
python tools/generate_record_vectors.py
python tools/validate_record_vectors.py
```

`generate_record_vectors.py` derives Record Identity and identity-preimage bytes exclusively through OLP APIs. `validate_record_vectors.py` verifies every positive identity and every expected negative Marketplace semantic failure.

The JSON vector representation uses OLP's implementation-neutral conformance projection. It is not a normative Marketplace wire format.
