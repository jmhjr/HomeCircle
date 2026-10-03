# Privacy and security

## Never commit

Real personal coordinates, home/dorm/work addresses, API keys (including Google and Azure browser keys), Life360 credentials/tokens/cookies, HA tokens, family photographs, precise travel/history records, private instance URLs, and unnecessary personal entity IDs. This applies to source, fixtures, screenshots, logs, copied YAML, bundles, ZIP files, Git history, issues and release assets.

Public examples use `person.example_member`, `device_tracker.example_phone`, `zone.example_residence`, and explicit fictional display names. Avoid real coordinates altogether in examples; use null when no position is necessary. New synthetic coordinate fixtures must be clearly documented and reviewed before allowing them in the privacy checker. Generic avatar initials/icons replace photos.

## Reference custody

The raw frozen snapshot lives outside the repository under the task's restricted `work/homecircle-reference-v1/` directory. Files are mode 600 and directories mode 700. This is access restriction, not encryption. It contains private dashboard configuration and must never be published or copied wholesale into Git. Its private manifest records original paths and SHA-256 digests; the public capture summary contains only generic artifact counts and evidence limitations.

Do not use whole Home Assistant backups, `.storage`, databases, or credential-only files as public development inputs. The snapshot deliberately excludes credential-only key files and does not pretend to be a full HA recovery backup. Existing source directories remain untouched.

## Runtime requirements

Use HA authentication and authorization. Do not expose unauthenticated household data. Keep provider credentials in their existing integrations. No analytics by default, no background exports, no new precise-location history store. Redact diagnostics by allowlisting safe fields; never log raw entity attributes, coordinates, address strings, tokens or requests containing them.

Show last-reported age honestly and distinguish unknown freshness. Location displays are informational, not a guarantee of safety or real-time presence. Give users control over which household members and fields are shown on shared displays. Kiosk presentation is not an access-control boundary.

External map tiles reveal viewed areas and client network metadata; geocoding/routing can transmit exact coordinates; radar providers receive tile requests. Explain each enabled service before opt-in. Restrict browser keys by origin and API, apply quotas, and never send server-only secrets to a browser. Optional provider failures must not erase basic HA presence.

When an HA person or selected tracker supplies a Life360 user or pet image, the card loads that portrait directly from `www.life360.com` or `life360-images-pub.life360.com`; Life360 receives the display's image request and network metadata. The card sends no HA page referrer. Other external image hosts are rejected, and initials remain visible if an image fails to load. HA-served portraits stay on the HA origin.

## Review and safeguards

`.gitignore` excludes private snapshots, secrets, credentials, images, archives and build products. The local pre-commit hook checks staged contents for common key/coordinate/address/entity patterns and unexpected binary files. Run `python3 scripts/check_public_files.py --all` before sharing. It is a conservative guard, not proof that a file is safe: inspect the diff and all generated release files manually. Do not bypass it to publish household data.

Before a release, review the complete Git history and release archive in addition to working files. Rotate/revoke exposed credentials at the issuing service if exposure occurs, remove sensitive history and artifacts, and follow the host's cleanup process; deleting a current file alone is insufficient.
