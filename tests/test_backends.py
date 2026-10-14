import json

import httpx
import pytest

from inspection_report.backends import ApiBackend, BackendError, LocalBackend, get_backend
from inspection_report.cli import main
from inspection_report.config import Settings

PNG = bytes.fromhex("89504e470d0a1a0a")


@pytest.fixture
def image(tmp_path):
    p = tmp_path / "tyre.png"
    p.write_bytes(PNG)
    return p


def make_backend(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ApiBackend("http://host/v1/", "m", "key", client=client)


def test_api_backend_sends_image_and_returns_text(image):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "worn tyre"}}]})

    assert make_backend(handler).describe(image, "check") == "worn tyre"
    assert seen["url"] == "http://host/v1/chat/completions"
    assert seen["auth"] == "Bearer key"
    parts = seen["body"]["messages"][0]["content"]
    assert parts[0] == {"type": "text", "text": "check"}
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_api_backend_wraps_http_and_shape_errors(image):
    with pytest.raises(BackendError):
        make_backend(lambda r: httpx.Response(500)).describe(image, "x")
    with pytest.raises(BackendError):
        make_backend(lambda r: httpx.Response(200, json={"oops": 1})).describe(image, "x")


def test_get_backend_selects_by_setting():
    assert isinstance(get_backend(Settings(backend="api")), ApiBackend)
    local = get_backend(Settings(backend="local", local_model="some/model"))
    assert isinstance(local, LocalBackend) and local.model_name == "some/model"


def test_describe_cli_reports_backend_error(image, monkeypatch, capsys):
    monkeypatch.setenv("INSPECTION_BACKEND", "api")
    monkeypatch.setenv("INSPECTION_API_BASE_URL", "http://127.0.0.1:9/v1")
    assert main(["describe", str(image)]) == 1
    assert "error:" in capsys.readouterr().err
