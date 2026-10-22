# Focused native activity regression validation

Canonical test source: 90cd91cb30d0291c422d554183c664717daa7832. Product runtime is unchanged from96a4175f18782ef27d4c05c656f6759ffe132088; package f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e.

The four new regressions cover projected item activity, retained history, restart and real setup ordering. Existing activity/provider setup/isolation tests also run. Core2026.10.2 dependencies are prepared online without owner state, then container networking is removed for pytest. This is focused pytest evidence only; it is not an HAOS upgrade/ordinary restore or full-suite result.

Source bytes and package members are checked before and after tests. Failure diagnostics contain only bounded public function/module identities, source line numbers and allowlisted exception classes. Cleanup is required.
