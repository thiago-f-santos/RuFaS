from io import BytesIO
import json
from urllib.error import HTTPError, URLError
import urllib.request
import pytest
from pytest_mock import MockerFixture
from RUFAS.adapters.exceptions import RemoteDataHttpError, RemoteDataConnectionError
from RUFAS.adapters.http_client import HttpClient
from RUFAS.adapters.schema import ServerConfig, RequestConfig

def test_http_client_get_success(mocker: MockerFixture) -> None:
    mock_response = BytesIO(b"sample_csv_data")
    mock_response.status = 200  # type: ignore[attr-defined]
    mock_urlopen = mocker.patch("urllib.request.urlopen", return_value=mock_response)

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com")
    request = RequestConfig(
        endpoint="/data",
        method="GET",
        headers={"Authorization": "Bearer test"},
        params={"year": "2020"},
    )
    result = client.execute(server, request)
    assert result == b"sample_csv_data"
    
    # Verify request construction
    assert mock_urlopen.call_count == 1
    req = mock_urlopen.call_args[0][0]
    assert isinstance(req, urllib.request.Request)
    assert req.full_url == "https://api.example.com/data?year=2020"
    assert req.get_method() == "GET"
    assert req.headers["Authorization"] == "Bearer test"

def test_http_client_post_json_body(mocker: MockerFixture) -> None:
    mock_response = BytesIO(b'{"status": "ok"}')
    mock_urlopen = mocker.patch("urllib.request.urlopen", return_value=mock_response)

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com/")
    payload = {"query": "weather", "lat": -18.5}
    request = RequestConfig(
        endpoint="query",  # without leading slash
        method="POST",
        body=payload,
    )
    result = client.execute(server, request)
    assert result == b'{"status": "ok"}'

    assert mock_urlopen.call_count == 1
    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://api.example.com/query"
    assert req.get_method() == "POST"
    assert req.data == json.dumps(payload).encode("utf-8")
    assert req.headers["Content-type"] == "application/json"

def test_http_client_post_string_and_bytes_body(mocker: MockerFixture) -> None:
    mock_urlopen = mocker.patch("urllib.request.urlopen", side_effect=lambda *args, **kwargs: BytesIO(b"ok"))

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com")

    # String body
    req_str = RequestConfig(endpoint="/raw", method="POST", body="raw_string_data")
    client.execute(server, req_str)
    req1 = mock_urlopen.call_args[0][0]
    assert req1.data == b"raw_string_data"

    # Bytes body
    req_bytes = RequestConfig(endpoint="/raw", method="POST", body=b"raw_bytes_data")
    client.execute(server, req_bytes)
    req2 = mock_urlopen.call_args[0][0]
    assert req2.data == b"raw_bytes_data"

def test_http_client_404_raises_http_error(mocker: MockerFixture) -> None:
    error = HTTPError("https://api.example.com/notfound", 404, "Not Found", {}, BytesIO(b"Resource missing"))  # type: ignore[arg-type]
    mocker.patch("urllib.request.urlopen", side_effect=error)

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com")
    request = RequestConfig(endpoint="/notfound", method="GET")
    with pytest.raises(RemoteDataHttpError, match="HTTP 404"):
        client.execute(server, request)

def test_http_client_timeout_raises_connection_error(mocker: MockerFixture) -> None:
    mocker.patch("urllib.request.urlopen", side_effect=URLError("Connection timed out"))

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com")
    request = RequestConfig(endpoint="/timeout", method="GET")
    with pytest.raises(RemoteDataConnectionError, match="Connection timed out"):
        client.execute(server, request)

def test_http_client_native_timeout_raises_connection_error(mocker: MockerFixture) -> None:
    mocker.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out"))

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com", timeout_seconds=10)
    request = RequestConfig(endpoint="/timeout", method="GET")
    with pytest.raises(RemoteDataConnectionError, match="timed out after 10s"):
        client.execute(server, request)

def test_http_client_generic_error_raises_connection_error(mocker: MockerFixture) -> None:
    mocker.patch("urllib.request.urlopen", side_effect=RuntimeError("DNS resolution failed"))

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com")
    request = RequestConfig(endpoint="/data", method="GET")
    with pytest.raises(RemoteDataConnectionError, match="Unexpected network error"):
        client.execute(server, request)


def test_http_client_preexisting_query_params(mocker: MockerFixture) -> None:
    mock_response = BytesIO(b"data")
    mock_urlopen = mocker.patch("urllib.request.urlopen", return_value=mock_response)

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com")
    request = RequestConfig(
        endpoint="/data?existing=1",
        method="GET",
        params={"extra": "2"},
    )
    result = client.execute(server, request)
    assert result == b"data"

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://api.example.com/data?existing=1&extra=2"


def test_http_client_lowercase_content_type(mocker: MockerFixture) -> None:
    mock_response = BytesIO(b"{}")
    mock_urlopen = mocker.patch("urllib.request.urlopen", return_value=mock_response)

    client = HttpClient()
    server = ServerConfig(base_url="https://api.example.com")
    request = RequestConfig(
        endpoint="/api",
        method="POST",
        headers={"content-type": "application/vnd.custom+json"},
        body={"foo": "bar"},
    )
    client.execute(server, request)

    req = mock_urlopen.call_args[0][0]
    # urllib capitalizes the header name to Content-type
    assert req.headers["Content-type"] == "application/vnd.custom+json"

