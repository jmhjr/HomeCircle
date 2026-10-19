"""Published FindMy 0.10.2 composer-only fixture (MIT; upstream LICENSE retained).

Extracted method bodies from the official PyPI wheel verified by its SHA256
2b367c0d59db66905e7e93ba828144ce473499aba5bfa17e89844a3169ffdde6.
No provider, native engine, session or network is constructed by this fixture.
"""
import base64
import plistlib
from typing import Any

UnhandledProtocolError = RuntimeError

class PublishedProvider:
    async def get_headers(
        self,
        user_id: str,
        device_id: str,
        serial: str = "0",
        with_client_info: bool = False,
    ) -> dict[str, str]:
        """
        Generate a complete dictionary of Anisette headers.

        Consider using :meth:`BaseAppleAccount.get_anisette_headers` instead.
        """
        headers = {
            # Current Time
            "X-Apple-I-Client-Time": self.timestamp,
            "X-Apple-I-TimeZone": self.timezone,
            # Locale
            "loc": self.locale,
            "X-Apple-Locale": self.locale,
            # 'One Time Password'
            "X-Apple-I-MD": self.otp,
            # 'Local User ID'
            "X-Apple-I-MD-LU": base64.b64encode(str(user_id).encode()).decode(),
            # 'Machine ID'
            "X-Apple-I-MD-M": self.machine,
            # 'Routing Info', some implementations convert this to an integer
            "X-Apple-I-MD-RINFO": self.router,
            # 'Device Unique Identifier'
            "X-Mme-Device-Id": str(device_id).upper(),
            # 'Device Serial Number'
            "X-Apple-I-SRL-NO": serial,
        }

        if with_client_info:
            headers["X-Mme-Client-Info"] = self.client
            headers["X-Apple-App-Info"] = "com.apple.gs.xcode.auth"
            headers["X-Xcode-Version"] = "11.2 (11B41)"

        return headers


    async def get_cpd(
        self,
        user_id: str,
        device_id: str,
        serial: str = "0",
    ) -> dict[str, str]:
        """
        Generate a complete dictionary of CPD data.

        Intended for internal use.
        """
        cpd = {
            "bootstrap": True,
            "icscrec": True,
            "pbe": False,
            "prkgen": True,
            "svct": "iCloud",
        }
        cpd.update(await self.get_headers(user_id, device_id, serial))

        return cpd


class PublishedAccount:
    async def _gsa_request(self, parameters: dict[str, Any]) -> dict[str, Any]:
        body = {
            "Header": {
                "Version": "1.0.1",
            },
            "Request": {
                "cpd": await self._anisette.get_cpd(
                    self._uid,
                    self._devid,
                ),
                **parameters,
            },
        }

        headers = {
            "Content-Type": "text/x-xml-plist",
            "Accept": "*/*",
            "User-Agent": "akd/1.0 CFNetwork/978.0.7 Darwin/18.7.0",
            "X-MMe-Client-Info": self._anisette.client,
        }

        resp = await self._http.post(
            self._ENDPOINT_GSA,
            headers=headers,
            data=plistlib.dumps(body),
        )
        if not resp.ok:
            msg = f"Error response for GSA request: {resp.status_code}"
            raise UnhandledProtocolError(msg)
        return resp.plist()["Response"]
