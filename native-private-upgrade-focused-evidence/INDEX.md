# Focused projected-item activity evidence

[Native run39818129202](https://github.com/jmhjr/HomeCircle/actions/runs/39818129202) passed all35 focused tests, with zero failures or skips. All four new regressions, including actual Home Assistant setup and unload cleanup, passed.

Canonical test source90cd91cb30d0291c422d554183c664717daa7832 changes no product bytes after runtime96a4175f18782ef27d4c05c656f6759ffe132088. Packagef181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e has113 members; its other111 members match the earlier98a package.

The exact runner and public-only source payload are retained at [57f39c0](https://github.com/jmhjr/HomeCircle/tree/57f39c0af3518640da8f139024e1ebe1fe2466fb/native-validation). The artifact ZIP here matches GitHub's digest and contains only bounded synthetic test summaries. Its diagnostics are not an acceptance result; candidate-summary and host cleanup are the acceptance records.

This is amd64 Core2026.10.2 focused pytest evidence. The container was disconnected before testing, source bytes were checked, and its container/private workspace were removed. It does not qualify a full backend run, managed HAOS upgrade, ordinary restore, real provider lifecycle or stable release. Private installation-copy evidence remains local; only its scoped high-level release note is public.
