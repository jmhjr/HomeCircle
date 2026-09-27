# ADR-001: Provider independence through standard Home Assistant entities

Status: Accepted 2026-09-27

## Context

The reference household dashboard grew around Life360-specific entities and attributes. That gives useful behavior evidence but creates account, credential, availability and private-API dependencies that should not define a reusable product. Home Assistant already provides the entity boundary for independently installed location integrations.

## Decision

HomeCircle consumes standard HA `person` and `device_tracker` entities, configured HA zones, and optional explicitly selected supporting sensors. People are the default onboarding unit; source trackers supply optional location details with provenance. Tracking integrations own authentication, collection, polling, and refresh.

No required Life360 integration, credential/token field, direct API client, bundled provider integration, provider-specific refresh loop, or account onboarding is permitted in HomeCircle core. Existing provider-specific raw units and report fields are reference details, not a universal data contract. Any future optional adapter must not be necessary for core presence and requires a separate decision.

## Consequences

Companion and other HA sources can work without changing product identity. Device capabilities and update frequency vary; driving, battery, report time and address may be absent. Normalize missing data explicitly, preserve HA presence semantics and source provenance, and never claim continuous tracking. Extra map/routing/weather services require independent opt-in and privacy disclosures.

## Alternatives rejected

A direct Life360 product would couple onboarding and availability to one provider. A browser-only copy of household YAML would preserve manual setup and duplicated rules. Neither satisfies provider-independent UI onboarding.

## Verification

V0.1 must function with Life360 absent. Exercise two independent sources, locationless trackers, source switching, and missing optional attributes. Audit dependencies, configuration forms and network calls for provider coupling.
