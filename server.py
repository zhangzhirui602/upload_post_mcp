import os
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("upload-post")


class UploadPostClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("UPLOADPOST_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing environment variable: UPLOADPOST_API_KEY")

        self.base_url = os.getenv("UPLOADPOST_BASE_URL", "https://api.upload-post.com/api").rstrip("/")
        self.publish_tiktok_path = os.getenv(
            "UPLOADPOST_PUBLISH_TIKTOK_PATH", "/v1/publish/tiktok"
        )
        self.check_status_path_template = os.getenv(
            "UPLOADPOST_CHECK_STATUS_PATH_TEMPLATE", "/v1/uploads/{upload_id}/status"
        )
        self.connected_accounts_path = os.getenv(
            "UPLOADPOST_CONNECTED_ACCOUNTS_PATH", "/uploadposts/users"
        )

        timeout_raw = os.getenv("UPLOADPOST_TIMEOUT", "30")
        self.timeout = float(timeout_raw)

        auth_header = self.api_key
        if not auth_header.lower().startswith("apikey "):
            auth_header = f"Apikey {self.api_key}"

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": auth_header,
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            }
        )

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self._build_url(path)
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            details = self._read_error_details(exc.response)
            raise RuntimeError(f"Upload-Post API HTTP error: {details}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Upload-Post API request failed: {exc}") from exc

    def _get(self, path: str) -> dict[str, Any]:
        url = self._build_url(path)
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            details = self._read_error_details(exc.response)
            raise RuntimeError(f"Upload-Post API HTTP error: {details}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Upload-Post API request failed: {exc}") from exc

    @staticmethod
    def _read_error_details(response: requests.Response | None) -> str:
        if response is None:
            return "No response body"
        try:
            return str(response.json())
        except ValueError:
            text = response.text.strip()
            return text or f"status={response.status_code}"


def _get_client() -> UploadPostClient:
    return UploadPostClient()


@mcp.tool()
def publish_video_to_tiktok(
    video_url: str,
    caption: str | None = None,
    scheduled_at: str | None = None,
    hashtags: list[str] | None = None,
    additional_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish a video to TikTok via Upload-Post API.

    Args:
        video_url: Publicly accessible video URL to publish.
        caption: Optional TikTok caption.
        scheduled_at: Optional ISO8601 schedule time.
        hashtags: Optional hashtag list (without #).
        additional_params: Optional extra API fields.
    """
    client = _get_client()
    payload: dict[str, Any] = {
        "video_url": video_url,
    }
    if caption is not None:
        payload["caption"] = caption
    if scheduled_at is not None:
        payload["scheduled_at"] = scheduled_at
    if hashtags:
        payload["hashtags"] = hashtags
    if additional_params:
        payload.update(additional_params)

    return client._post(client.publish_tiktok_path, payload)


@mcp.tool()
def check_upload_status(upload_id: str) -> dict[str, Any]:
    """Check Upload-Post task status by upload id."""
    client = _get_client()
    path = client.check_status_path_template.format(upload_id=upload_id)
    return client._get(path)


@mcp.tool()
def list_connected_accounts() -> dict[str, Any]:
    """List all accounts connected to the current Upload-Post API key."""
    client = _get_client()
    raw_response = client._get(client.connected_accounts_path)

    # Normalize different possible API response shapes into a flat account list.
    if isinstance(raw_response, list):
        accounts_source = raw_response
    else:
        accounts_source = (
            raw_response.get("accounts")
            or raw_response.get("data")
            or raw_response.get("items")
            or []
        )

    normalized_accounts: list[dict[str, Any]] = []
    if isinstance(accounts_source, list):
        for item in accounts_source:
            if not isinstance(item, dict):
                continue
            normalized_accounts.append(
                {
                    "account": item.get("account")
                    or item.get("platform")
                    or item.get("type")
                    or item.get("name"),
                    "user_identifier": item.get("user_identifier")
                    or item.get("userId")
                    or item.get("username")
                    or item.get("account_id")
                    or item.get("id"),
                    "raw": item,
                }
            )

    return {
        "connected_accounts": normalized_accounts,
        "raw_response": raw_response,
    }


if __name__ == "__main__":
    mcp.run()
