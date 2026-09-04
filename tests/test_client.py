from __future__ import annotations

from dataclasses import dataclass

import requests

from fabric_poc_automation.fabric.client import FabricClient


@dataclass
class Token:
    token: str = "test-token"


class Credential:
    def get_token(self, *_args, **_kwargs):
        return Token()


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return next(self.responses)


def response(status: int, body: dict | None = None, headers: dict | None = None) -> requests.Response:
    item = requests.Response()
    item.status_code = status
    item.headers.update(headers or {})
    if body is not None:
        import json
        item._content = json.dumps(body).encode()
        item.headers["Content-Type"] = "application/json"
    return item


def test_pagination_follows_continuation_uri() -> None:
    session = Session([
        response(200, {"value": [{"id": "1"}], "continuationUri": "https://next"}),
        response(200, {"value": [{"id": "2"}]}),
    ])
    client = FabricClient(Credential(), session=session)
    assert [item["id"] for item in client.list_all("/items")] == ["1", "2"]
    assert session.requests[1][1] == "https://next"


def test_synchronous_lro_result() -> None:
    client = FabricClient(Credential(), session=Session([]))
    result = client.wait_for_lro(response(201, {"id": "created"}))
    assert result.result == {"id": "created"}


def test_expected_empty_collection_404_can_be_handled_by_caller() -> None:
    session = Session([response(404, {"errorCode": "EnvironmentLibrariesNotFound"})])
    client = FabricClient(Credential(), session=session)
    result = client.request("GET", "/staging/libraries", expected=(200, 404))
    assert result.status_code == 404


def test_lro_success_with_no_result(monkeypatch) -> None:
    session = Session([
        response(200, {"status": "Succeeded"}),
        response(400, {"errorCode": "OperationHasNoResult"}),
    ])
    monkeypatch.setattr("fabric_poc_automation.fabric.client.time.sleep", lambda _seconds: None)
    client = FabricClient(Credential(), session=session)
    initial = response(202, headers={"Location": "https://operation", "Retry-After": "1"})
    result = client.wait_for_lro(initial)
    assert result.operation["status"] == "Succeeded"
    assert result.result is None


def test_transport_error_is_retried(monkeypatch) -> None:
    session = Session([requests.ConnectionError("reset"), response(200, {"value": []})])

    def request_with_exception(method, url, **kwargs):
        item = next(session.responses)
        if isinstance(item, Exception):
            raise item
        return item

    session.request = request_with_exception
    monkeypatch.setattr("fabric_poc_automation.fabric.client.time.sleep", lambda _seconds: None)
    client = FabricClient(Credential(), session=session)
    assert client.list_all("/items") == []
