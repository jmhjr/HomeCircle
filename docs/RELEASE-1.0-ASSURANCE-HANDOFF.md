# HomeCircle 1.0 cryptographic and format assurance handoff

Prepared October 20, 2026. This packet identifies evidence and unresolved
questions; it records no new audit, account exercise or release approval.

## Exact evidence boundary

- Tested canonical source: `9bf03eb45d2cf43274074534e9dfe2de841f4011`, 337 public
  files. The 113-member development ZIP is
  `c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861`;
  its inventory is
  `9bdfba997d5437d354673a98c8b78d3875d459499281bca3e20bc629369dcb6b`.
  It still reports `0.1.0-beta.20` and is unpublished. See
  [exact-source qualification](RELEASE-1.0-CORE-VALIDATION.md). This newly staged
  handoff is not part of that tested source snapshot.
- The [October 19 cryptographic review](INDEPENDENT-CRYPTO-VALIDATION.md) ended
  with local archive
  `f0477a91e78181fe1f8d80ada176a1739e10a7502abe7ee6ee2240571280d1f5`.
  Fresh archive comparison found all 74 Python members under `_vendor_findmy/`,
  `_findmy_runtime/` and top-level `findmy_*.py` byte-identical in c453.
  Changed archive members concern notices/provenance, version metadata,
  city lookup, normalization and frontend. This preserves the prior review's
  source relevance; it does not upgrade its assurance level or establish every
  target's dependency behavior.
- That review used fresh AI source reviews and generated positive/negative
  controls, not a human or external formal audit. No independent Apple-producer
  fixture or live account recovery was accepted. Its recorded Python, SRP and
  cryptography versions remain historical; record the actual resolved versions
  for each final target.

## Questions to resolve

1. **Trust and key binding:** confirm permanent-peer identity, signature context,
   recipient, view/UUID, recovered bottle keys and saved-account binding. State
   the reliance on the authenticated peer listing; complete voucher,
   dynamic-info, revocation and membership-history verification is not claimed.
2. **Supported records:** independently check PCS writable/read-only paths,
   current/extra key selection, optional versus supplied outer signatures,
   recipient ordering and authenticated accessory secret fields. Identify
   supported rotation/sharing forms and zone-default behavior. Attribute 7 and
   signer forms lacking trusted context currently fail closed; compatibility
   must not be inferred from rejection alone.
3. **Recovery framing and proof:** distinguish authenticated SRP/GCM and later
   material/bottle checks from tolerated KeyVault lengths/trailers and CBC's
   non-PKCS#7 fallback. Do not invent Apple padding/framing requirements or treat
   a valid 12-byte GCM nonce as a defect. Recheck bounds, cancellation drain,
   proof-dispatch guard and same-account/exact-record continuation.
4. **Reports:** retain the distinction between authenticated coordinates and
   outer timestamps/metadata. Successful decryption does not prove freshness or
   physical accuracy.

Generated fixtures, including round trips through library producers, remain
local controls. For interoperability evidence, identify an independently
produced vector, its provenance and independently established expected result;
pair supported success with safe malformed/unsupported rejection. Keep missing
producer evidence explicitly pending rather than relabeling generated data.

## Evidence and disposition

Return source/artifact and dependency versions, reviewed boundaries, fixed case
labels, results, confirmed findings and residual-risk dispositions. Fix and
recheck confirmed defects against identified bytes. The maintainer records the
remaining assurance and shipping decisions in the [release plan](RELEASE-1.0-PLAN.md);
this packet asserts no reviewer credentials or certification.

Use public or disposable synthetic material. Keep credentials, passcodes, keys,
raw account replies and locations private; do not deliberately submit a wrong
owner passcode. Any account work follows the separate
[controlled protocol](RELEASE-1.0-ACCOUNT-ACCEPTANCE.md), including newest-guard
preservation and the prepared restore boundary.

[Vendored origins](BETA20-VENDORED-ORIGINS.md), the
[dependency inventory](BETA20-DEPENDENCY-INVENTORY.md) and
[stable scope audit](STABLE-SCOPE-AUDIT.md) retain separate provenance, notice and
service-use questions. Technical assurance and supplemental notices do not close
those decisions; no legal conclusion is supplied here.
