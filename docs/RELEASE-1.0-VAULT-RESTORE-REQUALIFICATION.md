# Vault disconnect fix and restore requalification

October 21, 2026. Candidate source
`91ae59106a661143b770d7a3564d363c7c11a7dd` passed native package validation,
the eight-phase explicit disabled-entry partial-restore procedure and a separate
experimental offline saved-storage restore. The two earlier saved-storage
trials retain their failed outcomes. Stable-release gates remain open.

A malformed Apple vault key previously raised a constructor error outside the
vault error boundary, preventing an explicitly confirmed Disconnect from
removing an unreadable, owned account store. The candidate normalizes malformed
key and load-preflight filesystem errors to fixed vault errors, allowing the
existing confirmed removal path. Unsafe or legacy stores still refuse removal;
neither load nor save replaces a malformed key.

[Native package run 39683890536](https://github.com/jmhjr/HomeCircle/actions/runs/39683890536)
passed 1,698 backend cases, with zero failures and the existing optional skip;
all 122 frontend cases and 36 required regression functions passed. The old
vault produced exactly 14 expected failures with source-bound causes verified,
without collection errors or skips. The reproducible, unreleased beta 20
preview contains 113 runtime files and 617,791 ZIP bytes, SHA-256
`004c9bc4a968ad395e18033837cb42f5bd1d8719a8d90fc778fd20be4ff08f97`.
Only `findmy_vault.py` differs from the prior f4da650 runtime; the other 112
runtime files are unchanged. No owner accounts or production configuration
were used. Documentation changes are distinct from this tested runtime.

[Restore run 39685041916](https://github.com/jmhjr/HomeCircle/actions/runs/39685041916),
at controls `201438e28c8a5738c0c31193ba0b71d9f3451c51`, passed eight phases,
147 zero-skip contracts and both bounded offline guard-transfer contexts on
amd64/KVM, HAOS 18.3, Core 2026.10.2 and Supervisor 2026.10.3. Ordinary managed
dependencies, explicit selections, identities, settings, place, portrait,
dashboard/resource continuity and package bytes passed. Ten prebackup Recorder
rows returned, ten postbackup markers disappeared and ten new postrestore rows
survived restart.

Automatic restore returned older local guard 2 while HomeCircle was disabled
and unimported and the NIC closed. The procedure explicitly repaired the
separately retained newest guard 3 before enabling HomeCircle; the blocked
status survived restart. These synthetic counters do not measure Apple recovery
allowances. Each guard context preserved matching stopped managed-Core identity
before and after that individual context. Both containers, the disposable Linux
guest and its private workspace were cleaned up.

The nine-receipt artifact `12386541614` is 14,317 bytes, SHA-256
`eea9b7c087a1fd099d5b1b26de14e851ce89d1624a563b19259829fa3ede40a2`.
Independent replay accepted the procedure and cleanup; audit SHA-256
`c546158bb02fad377d8c3baab468ac7f19085b2377291010d2a0aa3c87d0a641`.
This account-free procedure does not establish saved provider storage recovery.

[Saved-storage run 39685990663](https://github.com/jmhjr/HomeCircle/actions/runs/39685990663)
at controls `630fb69` failed in its seed context, before any accepted phase,
backup or restore. The context was removed, managed Core remained stopped, the
NIC remained closed and guest/workspace cleanup passed. Its inner failure stage
was discarded. Independent negative audit `685a493a…` preserves that failure;
its precise runtime cause remains unknown.

Separately, primary Core 2026.10.2 code and execution of its exact file writer
confirmed that ordinary HA-managed stores use mode 0644, which the fixture
incorrectly rejected. Proof `546f7eaf…` establishes this compatibility defect;
it does not prove the failed run's cause. The child fixture accepts only 0600
or 0644 for the two exact owned HA stores, retains no-follow/type/owner/link/size
checks, and writes config replacements atomically as 0600. Private keys,
ciphertext, guard and proofs remain strict 0600. It also preserves only a fixed
action and allowlisted stage after a clean helper failure. All 97 local contracts
passed; product source and package bytes are unchanged.

[Corrected trial 39688084686](https://github.com/jmhjr/HomeCircle/actions/runs/39688084686),
at controls `e44ae2a104e3d74bb2f3191810a5ed8ab2aa115b`, failed after two
passed phases. Its seed and mutation contexts used a synthetic Apple session
encrypted by actual HomeCircle Vault/Fernet and synthetic Life360 credentials
in actual HA config-entry storage. Life360 has no separate HomeCircle encrypted
vault. HomeCircle remained disabled and unimported. The local partial backup,
archive inspection and separate newest-guard export passed. Supervisor refused
the restore request with `host_internet_unavailable` while the NIC remained
closed. No restore job ID was returned and no restore or guard import occurred.
All created contexts, the guest and private workspace were cleaned up. The
three-receipt artifact is 4,359 bytes, SHA-256
`ae2b621c09320634a268e24cabc54ac6693e24cbd952330ee551f4266f7b8dfd`;
independent negative audit SHA-256
`117beac4f3fb0dd33f6da866659afbe79d2179615a1e10d69515733f23adb530`.
This result does not establish saved-storage restoration and does not identify
the first trial's unretained seed failure.

[Experimental run 39691770592](https://github.com/jmhjr/HomeCircle/actions/runs/39691770592),
at controls `3c1e9e72e4ac2892b18b64473410987de237e427`, passed all five
phases, four storage contexts, two guard-transfer contexts and cleanup in
515.628 host seconds. All 112 zero-skip contracts passed in the native job.
The same candidate, local partial archive and verified cached Core image were
used, with the NIC closed throughout. HomeCircle stayed disabled and unimported
in managed Core. The synthetic Apple session was encrypted and reopened by
actual HomeCircle Vault/Fernet; synthetic Life360 credentials used actual HA
config-entry storage.

This was an experimental global, persisted Supervisor override that marks the
system unsupported while active. Only `internet_host` and `internet_system`
were temporarily ignored; all other job conditions remained enforced. The
original options were empty. A single apply and single reset each returned an
affirmative response, and both effective API options and the persisted options
were empty again in `finally` before guard repair or restored-vault validation.
No network reopening, owner credentials or provider activation was used. This
does not qualify ordinary/default Supervisor restore compatibility.

Automatic restore returned the baseline saved account/session storage,
explicit selections, registry joins and older guard 2. Newest guard 3 was kept
outside the entire guest and repaired before the first restored-vault load.
Both the post-restore and post-restart validators each passed 18 clone-only
fault cases, including key/ciphertext and identity/selection/registry refusal
checks. No-op save preserved the key/cipher pair; main storage remained
unchanged and all clones were removed. The subsequent disabled restart retained
those checks. Synthetic Recorder rollback and post-restore restart continuity
also passed. All six containers, the guest and private workspace were cleaned up.

The six-receipt artifact `12388977554` is 6,591 bytes, SHA-256
`b93ab07324a0361b2c23be8209df9c5ef918be778c4091231bcc91d769ca244b`.
Independent audit SHA-256:
`cb2cae2d257232a747668cdad7e9606f439e5df6944cc2840d6075e4c555d412`.
This accepts only the explicitly experimental disabled synthetic saved-storage
procedure; it does not reclassify either earlier failure.

Real-account authentication/session renewal after restore, ordinary enabled
restore safety, automatic guard antirollback, full-system/add-on/encrypted/cloud
backup, HACS/release-ZIP delivery, final RC and stable approval remain separate
gates. Provider/proof attempt counts are unmeasured. Historical f4da650 evidence
and earlier failures retain their outcomes.
[Machine-readable evidence](RELEASE-1.0-VAULT-RESTORE-REQUALIFICATION.json).


## Default-conditions restore follow-up

See [the default-conditions disabled saved-account restore record](RELEASE-1.0-DEFAULT-RESTORE.md)
for the separately reviewed procedure, its actual outcome when qualified, and the remaining release gates.
