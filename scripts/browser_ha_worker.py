"""Minimal browser QA Core worker; omit unrelated default integrations.

Uses real HA bootstrap, storage, authentication, frontend and lifecycle. The
parent supplies fresh temporary config; this is not a production launcher.
"""

import asyncio
import json
from pathlib import Path
import sys

from homeassistant import bootstrap, loader
from homeassistant.core import HomeAssistant


async def main():
    config_dir = sys.argv[1]
    hass = HomeAssistant(config_dir)
    loader.async_setup(hass)
    config = json.loads((Path(config_dir) / "configuration.yaml").read_text())
    if not await bootstrap.async_from_config_dict(config, hass):
        return 1
    return await hass.async_run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
