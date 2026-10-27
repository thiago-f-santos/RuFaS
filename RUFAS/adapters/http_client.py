import json
import urllib.error
import urllib.parse
import urllib.request
from RUFAS.adapters.exceptions import RemoteDataConnectionError, RemoteDataHttpError
from RUFAS.adapters.schema import RequestConfig, ServerConfig

class HttpClient:
    """Standard library HTTP client for remote data adapter requests."""

    def execute(self, server: ServerConfig, request: RequestConfig) -> bytes:
        url = server.base_url.rstrip("/")
        if request.endpoint:
            endpoint = request.endpoint if request.endpoint.startswith("/") else f"/{request.endpoint}"
            url += endpoint

        if request.params:
            query_string = urllib.parse.urlencode(request.params)
            url += f"&{query_string}" if "?" in url else f"?{query_string}"

        data: bytes | None = None
        headers = dict(request.headers)
        if request.body is not None:
            if isinstance(request.body, (dict, list)):
                data = json.dumps(request.body).encode("utf-8")
                has_content_type = any(k.lower() == "content-type" for k in headers)
                if not has_content_type:
                    headers["Content-Type"] = "application/json"
            elif isinstance(request.body, str):
                data = request.body.encode("utf-8")
            elif isinstance(request.body, bytes):
                data = request.body

        req = urllib.request.Request(
            url=url,
            data=data,
            headers=headers,
            method=request.method,
        )

        try:
            with urllib.request.urlopen(req, timeout=server.timeout_seconds) as response:
                return response.read()
        except urllib.error.HTTPError as he:
            snippet = ""
            try:
                snippet = he.read().decode("utf-8", errors="replace")[:200]
            except Exception:
                pass
            raise RemoteDataHttpError(
                f"HTTP {he.code} {he.reason} for {url}. Details: {snippet}"
            ) from he
        except urllib.error.URLError as ue:
            raise RemoteDataConnectionError(
                f"Failed to connect to {url}: {ue.reason}"
            ) from ue
        except TimeoutError as te:
            raise RemoteDataConnectionError(
                f"Request to {url} timed out after {server.timeout_seconds}s"
            ) from te
        except Exception as e:
            raise RemoteDataConnectionError(f"Unexpected network error connecting to {url}: {e}") from e
