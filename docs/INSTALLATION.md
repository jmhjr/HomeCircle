# Install and upgrade HomeCircle

Choose the store by your **Home Assistant Core** version, not the HAOS or Supervisor version. Find it under **Settings → About**.

| Home Assistant Core | Install and update with |
| --- | --- |
| 2026.11 and newer | Built-in **Settings → Marketplace** |
| 2026.9.4 through 2026.10.x | **HACS**, configured separately |
| Earlier than 2026.9.4 | Below HomeCircle's minimum supported Core version |

Use a published stable [HomeCircle release](https://github.com/jmhjr/HomeCircle/releases/latest), not a branch or GitHub source archive. Core 2026.11 requires **HomeCircle 1.0.1 or newer**. The integration ZIP includes the card.

Before changing an existing installation, make a Home Assistant backup including configuration and the Recorder/history you need. Protect it as account and location data, retain a copy outside the machine being changed, and keep it until the checks below pass. Existing households use the upgrade steps; adding HomeCircle again is not part of an update.

## Core 2026.11 and newer: Marketplace

Marketplace is included with Home Assistant and is available to administrators at **Settings → Marketplace**. Review its community-content notice if shown. See the [official Marketplace guide](https://www.home-assistant.io/integrations/marketplace/).

### Existing HACS installation after a Core upgrade

Home Assistant migrates HACS installations and custom repositories to Marketplace. HACS's entry and files are removed as part of that transition. Look for **HomeCircle** under **Marketplace → Installed** first. A missing HACS sidebar item does not call for reinstalling HACS, removing HomeCircle, or reconnecting its providers. Read [Home Assistant's migration notes](https://www.home-assistant.io/integrations/marketplace/#coming-from-hacs) if an entry is missing.

### New installation

1. Search Marketplace for **HomeCircle**. If its repository is already present, open it.
2. If it is absent, choose **Add from link**, enter `https://github.com/jmhjr/HomeCircle`, then select **Add**. Choose **Integration** if asked for the type.
3. A custom repository needs a GitHub connection. If prompted, use Marketplace's device sign-in flow and approve it on GitHub; return to Home Assistant to finish. Keep passwords, codes and tokens inside those services. An existing migrated connection may already satisfy this step.
4. Open HomeCircle, choose **Install**, check the offered stable version, and confirm. Use 1.0.1 or newer on Core 2026.11.
5. Restart Home Assistant. For a new household, open **Settings → Devices & services → Add integration → HomeCircle**, or continue the setup page if Marketplace opened it. Follow the [household setup guide](RELEASE-1.0-USER-GUIDE.md).

Installing files and creating a household are separate operations. Storage-mode setup registers the bundled card automatically; no separate card download or manual resource entry is required. YAML-managed resources keep their [separate frontend procedure](FRONTEND.md#ui-only-setup).

### Upgrade an existing HomeCircle installation

1. Open **Settings → Marketplace → Installed → HomeCircle**. An offered update can also appear under **Settings → Updates**.
2. Choose **Update**, review the installed and offered versions, then confirm the exact stable release you intend to install.
3. Wait for completion. Restart Home Assistant once to load the integration update, using the restart repair or Home Assistant's normal restart control.
4. Complete the checks below. Keep the existing HomeCircle entry, provider accounts and household selections.

## Core 2026.9.4 through 2026.10.x: HACS

Keep using HACS on these older supported Core versions. If it is not configured, follow the [official HACS setup instructions](https://www.hacs.dev/docs/use/download/download/); that installer is not the path for Core 2026.11 or newer.

1. In HACS, open **⋮ → Custom repositories**. Add `https://github.com/jmhjr/HomeCircle` with type **Integration** if it is absent. See [HACS custom repositories](https://www.hacs.dev/docs/faq/custom_repositories/).
2. Open HomeCircle. For a new installation, choose **Download**. For an existing one, use its update action or **⋮ → Redownload**. If the version picker is needed, open **Need a different version?** and select the intended published stable release. Do not substitute a branch commit or enable prereleases just to obtain a stable release.
3. Confirm the version and wait for the download to finish, then restart Home Assistant.
4. For a new household only, add HomeCircle under **Settings → Devices & services** and complete setup. For an upgrade, keep the existing entry and run the checks below.

## Verify after the restart

- Open **Settings → Devices & services → HomeCircle** and confirm the loaded version. Store download completion alone does not prove which version is running.
- Reload the browser if it still shows an earlier card. HomeCircle's card settings also shows its version.
- Check the household, Person/tracker associations, places, pictures, source-report ages and existing activity. Open the Life360 and Find My detail panels if you use those sources. An older source report can remain old after a successful update.
- If setup or the card fails, inspect [troubleshooting](RELEASE-1.0-TROUBLESHOOTING.md) and sanitized diagnostics. Do not remove/re-add provider accounts, reset safeguards or repeat Find My passcode recovery to repair an installation or cached card.

For rollback or a restored backup, use the [maintenance and recovery procedure](RELEASE-1.0-MAINTENANCE.md). Selecting an older package alone is not a safe data/account rollback procedure.
