# vectors/

Frozen x402 402 challenges that never change once published and can never be paid. Two independent probers who run
the checker against the same vector get the same answer, so their observations are comparable byte for byte. No Nano
budget is needed: nothing here is fetched or paid.

| file | frozen | what |
|---|---|---|
| `nano-exact-v1.json` | 2026-11-17 | x402 v2, `exact`, `nano:mainnet`, `XNO`, 1000000000000000000000000 raw, payTo = Nano burn address, `maxTimeoutSeconds` 300 |

Raw URL: `https://raw.githubusercontent.com/dhyabi2/xno-acceptance-registry/HEAD/vectors/nano-exact-v1.json`

Each vector carries the request that would produce it (`request`, URL on `.invalid` so it never resolves), the exact
402 body as one string (`response.body`, canonical JSON: sorted keys, separators `,` and `:`), its SHA-256
(`response.body_sha256`), the same bytes as an x402 v2 `PAYMENT-REQUIRED` header value
(`response.header_payment_required_b64`), and the fields a parser should read out (`expected_fields`).

`payTo` is `nano_1111111111111111111111111111111111111111111111111111hifc8npp`, the all-zero public key: the checksum
is valid, and anything sent there is lost, so the vector cannot be paid by mistake.

## Check a 402 you recorded

```
python3 vector_check.py --vector vectors/nano-exact-v1.json --observed FILE [--structure-only] \
    [--parser-client NAME --parser-version V]
```

`FILE` is the raw 402 body or the base64 `PAYMENT-REQUIRED` header value as received. Output is one JSON object
(`byte_identical`, `structural` per field `match`/`differs`/`missing`, `payTo_checksum_valid`, `parser_profile`, a
`challenge` block in the challenge-profile receipt's shape, `outcome: "observed"`).

- Exit 0: every field matches; without `--structure-only` the bytes must also be identical to `response.body`.
  With `--structure-only`, `amount_raw` and `payTo` may differ (a real seller quotes its own).
- Exit 1: mismatch, or `error` `no_accepts` / `no_nano_entry` / `payto_checksum`.
- Exit 2: input error, `error` `not_json` / `vector_corrupt` / `vector_not_frozen`.

## Freeze rule

A published vector is never edited. `tests/test_vectors.py` pins `body_sha256` as a literal; any change is a new file
(`nano-exact-v2.json`).
