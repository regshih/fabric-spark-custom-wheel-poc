"""Small supported-v1 Fabric REST client with bounded retry and LRO polling."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import requests
from azure.core.credentials import TokenCredential
from azure.identity import AzureCliCredential, ChainedTokenCredential, DefaultAzureCredential

FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
TRANSIENT_STATUS = {429, 500, 502, 503, 504}
TERMINAL_JOB_STATUS = {"Completed", "Failed", "Cancelled", "Deduped"}

log = logging.getLogger(__name__)


class FabricApiError(RuntimeError):
    """Fabric error that includes useful service details but never auth headers."""

    def __init__(self, method: str, url: str, response: requests.Response):
        try:
            detail: Any = response.json()
        except ValueError:
            detail = response.text[:2000]
        super().__init__(f"Fabric API {method} {url} returned {response.status_code}: {detail}")
        self.status_code = response.status_code
        self.detail = detail


@dataclass(frozen=True)
class LongRunningResult:
    operation: dict[str, Any]
    result: dict[str, Any] | None


class FabricClient:
    def __init__(
        self,
        credential: TokenCredential,
        *,
        session: requests.Session | None = None,
        timeout_seconds: int = 1800,
        max_retries: int = 5,
    ) -> None:
        self.credential = credential
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @classmethod
    def authenticated(cls, *, timeout_seconds: int = 1800) -> FabricClient:
        # Azure CLI is deliberately first. The fallback supports managed identity,
        # developer credentials, or an explicitly configured service principal.
        credential = ChainedTokenCredential(
            AzureCliCredential(),
            DefaultAzureCredential(exclude_cli_credential=True),
        )
        return cls(credential, timeout_seconds=timeout_seconds)

    def _headers(self, content_type: str | None = "application/json") -> dict[str, str]:
        token = self.credential.get_token(FABRIC_SCOPE).token
        headers = {"Authorization": f"Bearer {token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        expected: Iterable[int] = (200,),
        content_type: str | None = "application/json",
        **kwargs: Any,
    ) -> requests.Response:
        url = path_or_url if path_or_url.startswith("http") else f"{FABRIC_API}{path_or_url}"
        expected_set = set(expected)
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=self._headers(content_type),
                    timeout=120,
                    **kwargs,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Fabric API {method} {url} failed after {self.max_retries + 1} transport attempts: {exc}"
                    ) from exc
                delay = min(2**attempt, 30)
                log.warning("Fabric transport error; retrying in %ss: %s", delay, exc)
                time.sleep(delay)
                continue
            if response.status_code in expected_set:
                return response
            if response.status_code not in TRANSIENT_STATUS or attempt == self.max_retries:
                raise FabricApiError(method, url, response)
            delay = int(response.headers.get("Retry-After", min(2**attempt, 30)))
            log.warning("Fabric returned %s; retrying in %ss", response.status_code, delay)
            time.sleep(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def json_or_none(response: requests.Response) -> dict[str, Any] | None:
        return response.json() if response.content else None

    def wait_for_lro(self, response: requests.Response) -> LongRunningResult:
        if response.status_code != 202:
            body = self.json_or_none(response)
            return LongRunningResult(operation={"status": "Succeeded"}, result=body)
        location = response.headers.get("Location")
        if not location:
            raise RuntimeError("Fabric returned 202 without the required Location header")
        deadline = time.monotonic() + self.timeout_seconds
        retry_after = int(response.headers.get("Retry-After", 5))
        while time.monotonic() < deadline:
            time.sleep(max(retry_after, 1))
            poll = self.request("GET", location, expected=(200, 202))
            retry_after = int(poll.headers.get("Retry-After", retry_after))
            body = self.json_or_none(poll) or {}
            status = str(body.get("status", "")).lower()
            if status in {"succeeded", "completed"}:
                result = None
                result_url = body.get("resultLocation") or f"{location.rstrip('/')}/result"
                try:
                    result_response = self.request("GET", result_url, expected=(200, 204))
                    result = self.json_or_none(result_response)
                except FabricApiError as exc:
                    error_code = exc.detail.get("errorCode") if isinstance(exc.detail, dict) else None
                    if exc.status_code != 404 and error_code != "OperationHasNoResult":
                        raise
                return LongRunningResult(operation=body, result=result)
            if status in {"failed", "cancelled", "canceled"}:
                raise RuntimeError(f"Fabric long-running operation {status}: {body}")
        raise TimeoutError(f"Fabric operation did not finish within {self.timeout_seconds}s: {location}")

    def list_all(self, path: str, key: str = "value") -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        next_url: str | None = path
        while next_url:
            response = self.request("GET", next_url)
            body = response.json()
            values.extend(body.get(key, []))
            next_url = body.get("continuationUri")
        return values

    def list_workspaces(self) -> list[dict[str, Any]]:
        return self.list_all("/workspaces")

    def list_items(self, workspace_id: str) -> list[dict[str, Any]]:
        return self.list_all(f"/workspaces/{workspace_id}/items")

    def find_item(self, workspace_id: str, display_name: str, item_type: str) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self.list_items(workspace_id)
                if item.get("displayName") == display_name and item.get("type") == item_type
            ),
            None,
        )

    def run_item_job(
        self,
        workspace_id: str,
        item_id: str,
        job_type: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self.request(
            "POST",
            f"/workspaces/{workspace_id}/items/{item_id}/jobs/{job_type}/instances",
            json=body,
            expected=(202,),
        )
        return self._poll_job_response(response)

    def run_notebook(
        self,
        workspace_id: str,
        notebook_id: str,
        *,
        parameters: list[dict[str, Any]],
        environment_id: str,
        lakehouse_id: str,
    ) -> dict[str, Any]:
        body = {
            "parameters": parameters,
            "executionData": {
                "compute": "Spark",
                "computeConfiguration": {
                    "attachedEnvironment": {
                        "referenceType": "ById",
                        "itemId": environment_id,
                        "workspaceId": workspace_id,
                    },
                    "defaultLakehouse": {
                        "referenceType": "ById",
                        "itemId": lakehouse_id,
                        "workspaceId": workspace_id,
                    },
                },
            },
        }
        response = self.request(
            "POST",
            f"/workspaces/{workspace_id}/notebooks/{notebook_id}/jobs/execute/instances?beta=false",
            json=body,
            expected=(202,),
        )
        return self._poll_job_response(response)

    def run_pipeline(self, workspace_id: str, pipeline_id: str) -> dict[str, Any]:
        response = self.request(
            "POST",
            f"/workspaces/{workspace_id}/dataPipelines/{pipeline_id}/jobs/execute/instances",
            expected=(202,),
        )
        return self._poll_job_response(response)

    def _poll_job_response(self, response: requests.Response) -> dict[str, Any]:
        location = response.headers.get("Location")
        if not location:
            raise RuntimeError("Fabric job submission returned 202 without Location")
        retry_after = int(response.headers.get("Retry-After", 10))
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            time.sleep(max(retry_after, 1))
            status_response = self.request("GET", location)
            retry_after = int(status_response.headers.get("Retry-After", retry_after))
            status = status_response.json()
            if status.get("status") in TERMINAL_JOB_STATUS:
                if status["status"] != "Completed":
                    raise RuntimeError(f"Fabric job {status['status']}: {status}")
                return status
        raise TimeoutError(f"Fabric job did not finish within {self.timeout_seconds}s: {location}")
