from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
from typing import Any
from RUFAS.adapters.exceptions import RemoteConfigValidationError

@dataclass
class ServerConfig:
    base_url: str
    timeout_seconds: float = 30.0

@dataclass
class RequestConfig:
    endpoint: str = ""
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: Any | None = None

@dataclass
class CacheConfig:
    enabled: bool = True
    directory: str = "input/remote_cache"
    force_refresh: bool = False

@dataclass
class FileMapping:
    source_path: str
    destination_path: str
    metadata_key: str | None = None

@dataclass
class MappingConfig:
    type: str = "archive"  # "archive" or "direct_file"
    archive_format: str = "zip"  # "zip", "tar", "tar.gz", "tar.bz2"
    files: list[FileMapping] = field(default_factory=list)
    scenario_metadata: str | None = None

@dataclass
class RemoteConfig:
    name: str
    server: ServerConfig
    request: RequestConfig
    mapping: MappingConfig
    version: str = "1.0"
    cache: CacheConfig = field(default_factory=CacheConfig)

def _interpolate_string(val: str, params: dict[str, str]) -> str:
    pattern = re.compile(r"\$\{([A-Za-z0-9_]+)\}")
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in params:
            return params[key]
        if key in os.environ:
            return os.environ[key]
        raise RemoteConfigValidationError(f"Unresolved configuration parameter: '${{{key}}}'")
    return pattern.sub(replacer, val)

def _interpolate_obj(obj: Any, params: dict[str, str]) -> Any:
    if isinstance(obj, str):
        return _interpolate_string(obj, params)
    elif isinstance(obj, dict):
        return {k: _interpolate_obj(v, params) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_interpolate_obj(item, params) for item in obj]
    return obj

def load_remote_config(
    config_input: dict[str, Any] | Path | str,
    param_overrides: dict[str, str] | None = None,
) -> RemoteConfig:
    if isinstance(config_input, (Path, str)):
        path = Path(config_input)
        if not path.is_file():
            raise RemoteConfigValidationError(f"Remote configuration file not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            raise RemoteConfigValidationError(f"Failed to read remote configuration file '{path}': {e}") from e
    else:
        raw_data = dict(config_input)

    params = param_overrides or {}
    interpolated = _interpolate_obj(raw_data, params)

    try:
        server_data = interpolated.get("server", {})
        server = ServerConfig(
            base_url=server_data.get("base_url", "").rstrip("/"),
            timeout_seconds=float(server_data.get("timeout_seconds", 30.0)),
        )
        request_data = interpolated.get("request", {})
        request = RequestConfig(
            endpoint=request_data.get("endpoint", ""),
            method=request_data.get("method", "GET").upper(),
            headers={str(k): str(v) for k, v in request_data.get("headers", {}).items()},
            params={str(k): str(v) for k, v in request_data.get("params", {}).items()},
            body=request_data.get("body", None),
        )
        cache_data = interpolated.get("cache", {})
        cache = CacheConfig(
            enabled=bool(cache_data.get("enabled", True)),
            directory=str(cache_data.get("directory", "input/remote_cache")),
            force_refresh=bool(cache_data.get("force_refresh", False)),
        )
        mapping_data = interpolated.get("mapping", {})
        files = [
            FileMapping(
                source_path=str(f["source_path"]),
                destination_path=str(f["destination_path"]),
                metadata_key=f.get("metadata_key"),
            )
            for f in mapping_data.get("files", [])
        ]
        mapping = MappingConfig(
            type=str(mapping_data.get("type", "archive")),
            archive_format=str(mapping_data.get("archive_format", "zip")),
            files=files,
            scenario_metadata=mapping_data.get("scenario_metadata"),
        )
        return RemoteConfig(
            name=str(interpolated.get("name", "remote_adapter")),
            version=str(interpolated.get("version", "1.0")),
            server=server,
            request=request,
            cache=cache,
            mapping=mapping,
        )
    except KeyError as ke:
        raise RemoteConfigValidationError(f"Missing required configuration key: {ke}") from ke
    except Exception as e:
        raise RemoteConfigValidationError(f"Invalid remote configuration: {e}") from e
