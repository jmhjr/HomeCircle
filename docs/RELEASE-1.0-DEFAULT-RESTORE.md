# Default-conditions disabled saved-account restore

October 21, 2026. Candidate source
`91ae59106a661143b770d7a3564d363c7c11a7dd` passed the scoped default-conditions
saved-storage procedure in [run 39697883468](https://github.com/jmhjr/HomeCircle/actions/runs/39697883468),
at QA controls `18cdbf68819608180289bcfff9723e3cd5754fe9`. The disposable
amd64/KVM guest used HAOS 18.3, Core 2026.10.2 and Supervisor 2026.10.3.
The host completed in 535.006 seconds; independent replay accepted the workflow,
all five phases, four storage contexts, two guard contexts and final cleanup.

This qualifies only an ordinary Supervisor partial restore of USER-disabled,
synthetic saved-account storage with manual newest-guard repair. HomeCircle
remained disabled and unimported. Actual HomeCircle Vault/Fernet encrypted and
reopened the synthetic Apple session; synthetic Life360 credentials used actual
HA config-entry storage, with no separate Life360 encrypted vault. Explicit
selection, registry joins, identity records and saved configuration survived.
All 118 zero-skip contracts and all five process-specific boot grants passed.

The unchanged 113-member runtime ZIP is 617,791 bytes, SHA-256 `004c9bc4…`.
Native package validation, earlier account-free restore evidence and original
vault-disconnect fix are retained in [the requalification record](RELEASE-1.0-VAULT-RESTORE-REQUALIFICATION.md).
This QA/documentation work changes no runtime member. The retained owner-instance
witness is for f4da650; it does not establish installation of source91.

Supervisor conditions stayed enforced. There were zero jobs/options mutations,
no reset and no global or unsupported override. Effective options were empty
and persisted options were empty or absent before and after the restore window.
One read-only readiness observation found both host and Supervisor internet
conditions true. The disposable guest's external NIC opened only for ordinary
restore, with one acknowledged opening and one acknowledged closure. Positive
and negative probes, guest-agent availability and final default-option checks
passed. The 32 closed-network observations and all guard/vault contexts preserved
the closed boundary required outside that window.

Every helper boot published metadata and waited for a one-use grant targeting
its exact live process and phase before reading baseline, selection, key, vault
or guard state. The postrestore grant followed affirmative restore completion
and verified FINALLY closure/defaults. Automatic restore returned the baseline
storage and older guard 2. Newest guard 3 was retained outside the entire guest
and explicitly repaired before restored-vault loading. The five-phase guard
timeline was 2, 3, 2, 3, 3; these synthetic counters do not measure Apple allowances.

Both restored and restarted validators each passed 18 clone-only negative
cases, no-op pair preservation and unchanged-main-store checks. All clones were
removed. Six prebackup Recorder rows returned, six postbackup markers vanished,
and six new postrestore rows survived restart. All six contexts, the disposable
guest and its private workspace were cleaned up.

The first default-conditions trial, [run 39696526162](https://github.com/jmhjr/HomeCircle/actions/runs/39696526162),
remains negative: stopped synthetic seed/Fernet passed, but no managed phase,
backup/restore request, guard transfer or restore-window reopening followed.
It failed with `guest_command_failed` at `baseline_disabled`; cleanup passed.
Its inner command error was not retained. A separate source reproduction
confirmed that the grant writer used a VM-host path inside the Supervisor
container, whose configuration view is `/data/homeassistant`. The earlier local
test collapsed those namespaces and masked the mismatch. The correction changes
only the writer destination; host prechecks/request reads stay unchanged.
Namespace-preserving regressions retain all 116 prior contract identities and
add two cases. The exact R5 runtime failing site remains unproven.

R2 and R3 also retain their failed outcomes; R2's precise inner cause is unknown,
while R3 refused restore with `host_internet_unavailable` after seed, mutation,
backup and guard export passed. R4 retains only its separately accepted
experimental global, persisted, unsupported override result. The seven audit
roles and their full digests remain in the companion record.

The six-receipt artifact `12392290513` is 6,727 bytes, SHA-256
`090dee1da28481f17f5d106aaa81f86d4230655fb4366dd58931b615a47104cf`.
Independent audit SHA-256:
`5e136cc8a1451e69e064d965b49176c91542832151ce7a346ea53a5fcb90a23b`.

Enabled-provider restore, real-account authentication/renewal, automatic guard
antirollback, full-system/add-on/encrypted/cloud backup, HACS delivery, final RC
and stable approval remain unqualified. Provider/proof attempt counts remain
unmeasured. [Machine-readable evidence](RELEASE-1.0-DEFAULT-RESTORE.json).
