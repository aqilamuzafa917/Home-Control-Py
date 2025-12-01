"""Logic for authenticating against the Xiaomi cloud."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import certifi
import requests

try:
    from miio import Device  # type: ignore
except ImportError:  # pragma: no cover - dependency optional during dev
    Device = None  # type: ignore

try:
    from Crypto.Cipher import ARC4  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    try:
        from Cryptodome.Cipher import ARC4  # type: ignore
    except ImportError:
        ARC4 = None  # type: ignore

from .constants import DEFAULT_COUNTRY


def get_ssl_cert_path() -> str:
    """Return the certificate bundle location included with PyInstaller."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
        return os.path.join(base_path, "certifi", "cacert.pem")
    except Exception:
        return certifi.where()


class XiaomiCloudEngine:
    """Encapsulates all Xiaomi cloud authentication and device calls."""

    def __init__(self) -> None:
        if ARC4 is None:
            raise RuntimeError("pycryptodome is required for Xiaomi login flow.")

        self._agent = self.generate_agent()
        self._device_id = self.generate_device_id()
        self._session = requests.session()
        self._session.verify = get_ssl_cert_path()
        self._ssecurity: str | None = None
        self.user_id: str | None = None
        self._service_token: str | None = None
        self._location: str | None = None
        self.login_url: str | None = None

    # --------------------------------------------------------------------- #
    # Static helpers
    # --------------------------------------------------------------------- #
    @staticmethod
    def generate_agent() -> str:
        import random

        agent_id = "".join(chr(random.randint(65, 69)) for _ in range(13))
        return f"ANDROID-APP-{agent_id} APP/com.xiaomi.mihome APPV/10.5.201"

    @staticmethod
    def generate_device_id() -> str:
        import random

        return "".join(chr(random.randint(97, 122)) for _ in range(6))

    @staticmethod
    def generate_nonce(millis: int) -> str:
        nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder="big")
        return base64.b64encode(nonce_bytes).decode()

    def signed_nonce(self, nonce: str) -> str:
        if not self._ssecurity:
            raise RuntimeError("ssecurity missing")
        hash_object = hashlib.sha256(base64.b64decode(self._ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(hash_object.digest()).decode("utf-8")

    @staticmethod
    def generate_enc_signature(url: str, method: str, signed_nonce: str, params: Dict[str, Any]) -> str:
        signature_params = [method.upper(), url.split("com")[1].replace("/app/", "/")]
        for key, value in params.items():
            signature_params.append(f"{key}={value}")
        signature_params.append(signed_nonce)
        signature_string = "&".join(signature_params)
        return base64.b64encode(hashlib.sha1(signature_string.encode("utf-8")).digest()).decode()

    def encrypt_rc4(self, password: str, payload: str) -> str:
        cipher = ARC4.new(base64.b64decode(password))
        cipher.encrypt(bytes(1024))
        return base64.b64encode(cipher.encrypt(payload.encode())).decode()

    def decrypt_rc4(self, password: str, payload: str) -> bytes:
        cipher = ARC4.new(base64.b64decode(password))
        cipher.encrypt(bytes(1024))
        return cipher.encrypt(base64.b64decode(payload))

    def generate_enc_params(
        self, url: str, method: str, signed_nonce: str, nonce: str, params: Dict[str, str]
    ) -> Dict[str, Any]:
        params["rc4_hash__"] = self.generate_enc_signature(url, method, signed_nonce, params)
        for key, value in list(params.items()):
            params[key] = self.encrypt_rc4(signed_nonce, value)

        params.update(
            {
                "signature": self.generate_enc_signature(url, method, signed_nonce, params),
                "ssecurity": self._ssecurity,
                "_nonce": nonce,
            }
        )
        return params

    @staticmethod
    def get_api_url(country: str) -> str:
        prefix = "" if country == "cn" else f"{country}."
        return f"https://{prefix}api.io.mi.com/app"

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def execute_api_call_encrypted(self, url: str, params: Dict[str, str]) -> Any:
        if not self.user_id or not self._service_token or not self._ssecurity:
            raise RuntimeError("Missing Xiaomi session context.")

        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
        }
        cookies = {
            "userId": str(self.user_id),
            "serviceToken": str(self._service_token),
            "locale": "en_GB",
        }

        millis = round(time.time() * 1000)
        nonce = self.generate_nonce(millis)
        signed_nonce = self.signed_nonce(nonce)
        fields = self.generate_enc_params(url, "POST", signed_nonce, nonce, params)
        response = self._session.post(url, headers=headers, cookies=cookies, params=fields, timeout=30)
        response.raise_for_status()
        decoded = self.decrypt_rc4(self.signed_nonce(fields["_nonce"]), response.text)
        return json.loads(decoded)

    def step_1_get_qr(self) -> tuple[str | None, str | None]:
        url = "https://account.xiaomi.com/longPolling/loginUrl"
        data = {
            "_qrsize": "240",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "callback": "https://sts.api.io.mi.com/sts",
            "_hasLogo": "false",
            "sid": "xiaomiio",
            "_locale": "en_GB",
            "_dc": str(int(time.time() * 1000)),
        }
        resp = self._session.get(url, params=data, timeout=30)
        resp.raise_for_status()
        payload = json.loads(resp.text.replace("&&&START&&&", ""))
        self.login_url = payload.get("loginUrl")
        return payload.get("qr"), payload.get("lp")

    def step_2_download_img(self, url: str) -> bytes:
        resp = self._session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    def step_3_poll(self, lp_url: str) -> bool:
        while True:
            resp = self._session.get(lp_url, timeout=10)
            if resp.status_code != 200:
                continue
            payload = json.loads(resp.text.replace("&&&START&&&", ""))
            self.user_id = payload["userId"]
            self._ssecurity = payload["ssecurity"]
            self._location = payload["location"]
            return True

    def step_4_service_token(self) -> bool:
        if not self._location:
            return False
        resp = self._session.get(self._location, timeout=30)
        if resp.status_code == 200:
            self._service_token = resp.cookies.get("serviceToken")
            return self._service_token is not None
        return False

    def get_devices(self, country: str = DEFAULT_COUNTRY) -> list[dict[str, Any]]:
        base_url = self.get_api_url(country)
        homes = self.execute_api_call_encrypted(
            f"{base_url}/v2/homeroom/gethome",
            {"data": '{"fg": true, "limit": 100}'},
        )

        if not homes or "result" not in homes or not homes["result"].get("homelist"):
            return []

        home_id = homes["result"]["homelist"][0]["id"]
        params = {
            "data": json.dumps(
                {
                    "home_owner": self.user_id,
                    "home_id": home_id,
                    "limit": 200,
                    "get_split_device": True,
                }
            )
        }
        result = self.execute_api_call_encrypted(f"{base_url}/v2/home/home_device_list", params)
        return result.get("result", {}).get("device_info", []) if result else []


__all__ = ["XiaomiCloudEngine", "Device"]

