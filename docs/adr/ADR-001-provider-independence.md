# ADR-001: Provider independence through standard Home Assistant entities

Status: Accepted 2026-09-27

## Context

The reference household dashboard grew around Life360-specific entities and attributes. That gives useful behavior evidence but creates account, credential, availability and private-API dependencies that should not define a reusable product. Home Assistant already provides the entity boundary for independently installed location integrations.

## Decision

HomeCircle consumes standard HA `person` and `device_tracker` entities, configured HA zones, and optional explicitly selected supporting sensors. People are the default onboarding unit; source trackers supply optional location details with provenance. Tracking integrations own authentication, collection, polling, and refresh.

No required Life360 integration, credential/token field, direct API client, bundled provider integration, provider-specific refresh loop, or account onboarding is permitted in HomeCircle core. Existing provider-specific raw units and report fields are reference details, not a universal data contract. Any future optional adapter must not be necessary for core presence and requires a separate decision.

## 2026-10-04 optional-provider amendment

The user approved an optional direct Life360 connection, implemented in beta 11 and retained in beta 16. It creates ordinary HA `device_tracker` entities behind the same person/tracker selection and normalization boundary. The `life360` client is a package dependency, but HomeCircle makes no provider connection unless the user enables and verifies an account. Households using existing HA trackers still require no Life360 credentials. The shared provider contract separates credentials, entity ownership, polling, health and reauthentication so future providers can be added independently. The original prohibition above continues to apply to **required core behavior**; the optional adapter is the approved exception. See [architecture](../ARCHITECTURE.md) and the [provider issue workflow](../TRACKER-PROVIDER-ISSUES.md).

## Consequences

Companion and other HA sources can work without changing product identity. Device capabilities and update frequency vary; driving, battery, report time and address may be absent. Normalize missing data explicitly, preserve HA presence semantics and source provenance, and never claim continuous tracking. Extra map/routing/weather services require independent opt-in and privacy disclosures.

## Alternatives rejected

A direct Life360 product would couple onboarding and availability to one provider. A browser-only copy of household YAML would preserve manual setup and duplicated rules. Neither satisfies provider-independent UI onboarding.

## Verification

V0.1 must function with Life360 absent. Exercise two independent sources, locationless trackers, source switching, and missing optional attributes. Audit dependencies, configuration forms and network calls for provider coupling.
