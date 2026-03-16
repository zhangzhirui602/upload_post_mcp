import os
import mimetypes
import time
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
        self.check_status_path = os.getenv(
            "UPLOADPOST_CHECK_STATUS_PATH", "/uploadposts/status"
        )
        self.connected_accounts_path = os.getenv(
            "UPLOADPOST_CONNECTED_ACCOUNTS_PATH", "/uploadposts/users"
        )
        self.upload_asset_path = os.getenv("UPLOADPOST_UPLOAD_ASSET_PATH", "/upload")
        self.upload_file_field = os.getenv("UPLOADPOST_UPLOAD_FILE_FIELD", "video")

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

    def _post_multipart(
        self,
        path: str,
        data: dict[str, Any],
        files: dict[str, Any],
    ) -> dict[str, Any]:
        url = self._build_url(path)
        headers = dict(self.session.headers)
        headers.pop("Content-Type", None)
        try:
            response = self.session.post(
                url,
                data=data,
                files=files,
                headers=headers,
                timeout=self.timeout,
            )
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


def _extract_uploaded_video_url(upload_response: dict[str, Any]) -> str | None:
    direct_candidates = [
        upload_response.get("video_url"),
        upload_response.get("file_url"),
        upload_response.get("url"),
    ]
    for candidate in direct_candidates:
        if isinstance(candidate, str) and candidate:
            return candidate

    data = upload_response.get("data")
    if isinstance(data, dict):
        for key in ("video_url", "file_url", "url"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value

    result = upload_response.get("result")
    if isinstance(result, dict):
        for key in ("video_url", "file_url", "url"):
            value = result.get(key)
            if isinstance(value, str) and value:
                return value

    return None


def _extract_default_profile_username(profiles_response: dict[str, Any]) -> str | None:
    profiles = profiles_response.get("profiles")
    if not isinstance(profiles, list):
        return None
    for item in profiles:
        if not isinstance(item, dict):
            continue
        username = item.get("username")
        if isinstance(username, str) and username:
            return username
    return None


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
def publish_local_video_to_tiktok(
    local_file_path: str,
    user: str | None = None,
    caption: str | None = None,
    scheduled_at: str | None = None,
    hashtags: list[str] | None = None,
    upload_additional_params: dict[str, Any] | None = None,
    publish_additional_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upload a local video file first, then publish it to TikTok.

    Args:
        local_file_path: Absolute or relative local video file path.
        user: Upload-Post profile username. If omitted, auto-uses first profile.
        caption: Optional TikTok caption.
        scheduled_at: Optional ISO8601 schedule time.
        hashtags: Optional hashtag list (without #).
        upload_additional_params: Optional extra form fields for upload API.
        publish_additional_params: Optional extra JSON fields for publish API.
    """
    client = _get_client()

    normalized_path = os.path.abspath(local_file_path)
    if not os.path.isfile(normalized_path):
        raise RuntimeError(f"Local video file not found: {normalized_path}")

    upload_payload = dict(upload_additional_params or {})

    if "user" not in upload_payload:
        if user:
            upload_payload["user"] = user
        else:
            profiles_response = client._get(client.connected_accounts_path)
            detected_user = _extract_default_profile_username(profiles_response)
            if detected_user:
                upload_payload["user"] = detected_user

    if "platform[]" not in upload_payload and "platform" not in upload_payload:
        upload_payload["platform[]"] = "tiktok"

    if "title" not in upload_payload and caption is not None:
        upload_payload["title"] = caption

    if "user" not in upload_payload:
        raise RuntimeError(
            "Missing upload user profile. Pass `user` parameter, or provide "
            "upload_additional_params.user."
        )

    # Preferred path: official SDK handles local-file upload and publish reliably.
    sdk_error: Exception | None = None
    try:
        from upload_post import UploadPostClient  # type: ignore

        sdk_client = UploadPostClient(client.api_key)
        title = str(upload_payload.get("title") or os.path.basename(normalized_path))
        if hashtags:
            hashtag_text = " ".join(f"#{tag}" for tag in hashtags if tag)
            if hashtag_text:
                title = f"{title} {hashtag_text}".strip()

        sdk_kwargs: dict[str, Any] = {}
        for key, value in upload_payload.items():
            if key in {"user", "title", "platform", "platform[]"}:
                continue
            sdk_kwargs[key] = value
        if scheduled_at is not None and "scheduled_date" not in sdk_kwargs:
            sdk_kwargs["scheduled_date"] = scheduled_at
        if publish_additional_params:
            sdk_kwargs.update(publish_additional_params)

        sdk_response = sdk_client.upload_video(
            video_path=normalized_path,
            title=title,
            user=str(upload_payload["user"]),
            platforms=["tiktok"],
            **sdk_kwargs,
        )
        sdk_result: dict[str, Any] = {
            "mode": "sdk_direct_upload_publish",
            "sdk_response": sdk_response,
        }
        if isinstance(sdk_response, dict) and sdk_response.get("request_id"):
            sdk_result["request_id"] = sdk_response["request_id"]
        return sdk_result
    except Exception as exc:  # noqa: BLE001
        sdk_error = exc

    filename = os.path.basename(normalized_path)
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"

    # Retry once for transient TLS reset issues (WinError 10054).
    upload_error: RuntimeError | None = None
    upload_response: dict[str, Any] | None = None
    for attempt in range(2):
        try:
            with open(normalized_path, "rb") as handle:
                upload_response = client._post_multipart(
                    client.upload_asset_path,
                    data=upload_payload,
                    files={
                        client.upload_file_field: (filename, handle, content_type),
                    },
                )
            break
        except RuntimeError as exc:
            upload_error = exc
            if attempt == 0:
                time.sleep(1.5)
                continue
            raise

    if upload_response is None:
        if upload_error is not None:
            if sdk_error is not None:
                raise RuntimeError(
                    "Both SDK upload and HTTP multipart fallback failed. "
                    f"SDK error: {sdk_error}; HTTP error: {upload_error}"
                ) from upload_error
            raise upload_error
        raise RuntimeError("Upload failed with unknown error")

    uploaded_video_url = _extract_uploaded_video_url(upload_response)
    # Some Upload-Post deployments publish directly on /upload and do not return video URL.
    if not uploaded_video_url and isinstance(upload_response, dict):
        if upload_response.get("success") is True:
            result: dict[str, Any] = {
                "mode": "direct_upload_publish",
                "upload_response": upload_response,
                "message": "Upload endpoint already handled publishing. No follow-up publish call required.",
            }
            # Surface request_id so callers can poll check_upload_status.
            req_id = upload_response.get("request_id")
            if req_id:
                result["request_id"] = req_id
                result["message"] += (
                    f" Use check_upload_status(request_id='{req_id}') to track progress."
                )
            return result

    if not uploaded_video_url:
        raise RuntimeError(
            "Upload succeeded but no video URL was found in response. "
            "Please pass correct upload fields/path via UPLOADPOST_UPLOAD_ASSET_PATH, "
            "UPLOADPOST_UPLOAD_FILE_FIELD or upload_additional_params. "
            f"Response: {upload_response}"
        )

    publish_payload: dict[str, Any] = {
        "video_url": uploaded_video_url,
    }
    if caption is not None:
        publish_payload["caption"] = caption
    if scheduled_at is not None:
        publish_payload["scheduled_at"] = scheduled_at
    if hashtags:
        publish_payload["hashtags"] = hashtags
    if publish_additional_params:
        publish_payload.update(publish_additional_params)

    publish_response = client._post(client.publish_tiktok_path, publish_payload)

    return {
        "uploaded_video_url": uploaded_video_url,
        "upload_response": upload_response,
        "publish_response": publish_response,
    }


@mcp.tool()
def check_upload_status(request_id: str) -> dict[str, Any]:
    """Check Upload-Post async task status by request_id."""
    client = _get_client()
    url = client._build_url(client.check_status_path)
    try:
        response = client.session.get(
            url, params={"request_id": request_id}, timeout=client.timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        details = client._read_error_details(exc.response)
        raise RuntimeError(f"Upload-Post API HTTP error: {details}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Upload-Post API request failed: {exc}") from exc


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
