"""Instagram API with Facebook Login for Business (Unified login, system-user token): resumable Reels upload."""
import logging
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)
GRAPH = "https://graph.facebook.com"
RUPLOAD = "https://rupload.facebook.com/ig-api-upload"
AUTH_ERROR_CODES = {10, 102, 190, 200}
TIMEOUT = 60
UPLOAD_TIMEOUT = 600


class AuthError(RuntimeError):
    pass


class PublishError(RuntimeError):
    pass


class Instagram:
    def __init__(self, cfg: dict, token: str, ig_user_id: str):
        ig = cfg["instagram"]
        self.version, self.user, self.ig = ig["graph_version"], ig_user_id, ig
        self.base = f"{GRAPH}/{self.version}"
        self._headers = {"Authorization": f"OAuth {token}"}     # header, never in URLs or logs

    def _call(self, method: str, url: str, **kwargs) -> dict:
        r = requests.request(method, url, headers={**self._headers, **kwargs.pop("headers", {})},
                             timeout=kwargs.pop("timeout", TIMEOUT), **kwargs)
        try:
            body = r.json()
        except ValueError:
            body = {}
        err = body.get("error") if isinstance(body, dict) else None
        if r.status_code in (401, 403) or (err and err.get("code") in AUTH_ERROR_CODES):
            raise AuthError(f"Instagram auth error {r.status_code}: {(err or {}).get('message', r.text[:200])}")
        if r.status_code >= 400 or err:
            raise PublishError(f"Instagram API {r.status_code}: {(err or {}).get('message', r.text[:300])}")
        return body

    def account(self) -> dict:
        return self._call("GET", f"{self.base}/{self.user}", params={"fields": "id,username"})

    def create_reel_container(self, caption: str) -> tuple[str, str]:
        """Returns (container id, upload uri). Meta returns the exact upload URI; use it as given."""
        data = {"media_type": "REELS", "upload_type": "resumable", "caption": caption}
        url = f"{self.base}/{self.user}/media"
        body = None
        if self.ig["share_to_feed"]:
            try:
                body = self._call("POST", url, data={**data, "share_to_feed": "true"})
            except PublishError as e:   # share_to_feed isn't documented for resumable uploads
                log.warning("container with share_to_feed rejected (%s); retrying without it", e)
        body = body or self._call("POST", url, data=data)
        uri = body.get("uri") or f"{RUPLOAD}/{self.version}/{body['id']}"
        log.info("container %s created; upload uri host %s", body["id"], uri.split("/")[2])
        return body["id"], uri

    def upload(self, upload_uri: str, video: Path) -> None:
        payload = video.read_bytes()          # reels are well under the 300 MB limit
        body = self._call("POST", upload_uri, data=payload, timeout=UPLOAD_TIMEOUT,
                          headers={"offset": "0", "file_size": str(len(payload)),
                                   "Content-Type": "application/octet-stream"})
        if not body.get("success"):
            raise PublishError(f"upload not accepted: {body}")

    def status(self, container_id: str) -> str:
        return self._call("GET", f"{self.base}/{container_id}", params={"fields": "status_code,status"}).get(
            "status_code", "UNKNOWN")

    def wait_until_ready(self, container_id: str) -> None:
        deadline = time.monotonic() + self.ig["poll_timeout_seconds"]
        while time.monotonic() < deadline:
            info = self._call("GET", f"{self.base}/{container_id}", params={"fields": "status_code,status"})
            code = info.get("status_code")
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise PublishError(f"container {code}: {info.get('status')}")
            time.sleep(self.ig["poll_seconds"])
        raise PublishError("container not FINISHED before the polling timeout")

    def publish(self, container_id: str) -> str:
        return self._call("POST", f"{self.base}/{self.user}/media_publish", data={"creation_id": container_id})["id"]

    def recent_media(self, limit: int = 25) -> list[dict]:
        params = {"fields": "id,caption,timestamp,media_product_type", "limit": limit}
        return self._call("GET", f"{self.base}/{self.user}/media", params=params).get("data", [])
