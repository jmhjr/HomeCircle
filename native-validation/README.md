# Native current Core focused checks

This preparation adapts the already installed `native-amd64-validation.yml` workflow
without changing its YAML or requesting workflow permissions. Publish this directory
as `native-validation/` on the QA branch after reviewing and filling every input pin.
The existing push path filter starts it. The old workflow display name is historical;
all receipts explicitly qualify only focused pytest execution on native Linux AMD64.

Inputs are a canonical source tarball and per-file inventory, the matching development
package and inventory, and `payload/config.json` filled from the example. Set
`CONFIG.sha256` to the final configuration digest after pinning `driver.py` and all
payload bytes. Any pending template value fails closed before a container is created.
The source commit is verified by exact Git blob readback; a shallow checkout fetches
only the pinned public commit if needed. No credentials or owner state enter the guest.

The pinned Core 2026.10.2 image and exact Core constraints prepare the matching
pytest-homeassistant-custom-component 0.13.373 package and declared dependencies.
The container has no host mounts or published ports. Networking is disconnected and
checked before pytest. All four new projection tests and the existing activity,
provider setup and startup-isolation modules must pass with no skips or errors.
Receipts name every observed passing case. Private test output is deleted after
collecting only fixed-label JSON receipts and proving owned container cleanup.

This does not repeat the complete backend suite, run a managed Core lifecycle,
exercise KVM, validate an upgrade, use owner accounts or publish a release.

The second source revision corrects only the synthetic setup fixture to provide explicit selected residence IDs. Product files and the f181 package are unchanged. Original failed runs remain separate evidence.
