import json
import os
from pathlib import Path
import pytest
from RUFAS.adapters.exceptions import (
    ArchiveExtractionError,
    ArchiveMappingError,
    ArchiveSecurityError,
    RemoteAdapterError,
    RemoteConfigValidationError,
    RemoteDataConnectionError,
    RemoteDataHttpError,
)
from RUFAS.adapters.schema import (
    CacheConfig,
    FileMapping,
    MappingConfig,
    RemoteConfig,
    RequestConfig,
    ServerConfig,
    load_remote_config,
)

def test_load_remote_config_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_data = {
        "name": "test_service",
        "version": "1.0",
        "server": {"base_url": "https://example.com/api", "timeout_seconds": 15},
        "request": {
            "endpoint": "/weather/${YEAR}",
            "method": "GET",
            "headers": {"Authorization": "Bearer ${API_KEY}"},
            "params": {"county": "55025"},
            "body": None,
        },
        "cache": {"enabled": True, "directory": "input/remote_cache", "force_refresh": False},
        "mapping": {
            "type": "archive",
            "archive_format": "zip",
            "files": [
                {
                    "source_path": "weather.csv",
                    "destination_path": "input/data/weather/downloaded.csv",
                    "metadata_key": "weather",
                }
            ],
            "scenario_metadata": None,
        },
    }
    overrides = {"YEAR": "2020"}
    monkeypatch.setenv("API_KEY", "secret123")
    config = load_remote_config(config_data, param_overrides=overrides)
    assert isinstance(config, RemoteConfig)
    assert config.server.base_url == "https://example.com/api"
    assert config.server.timeout_seconds == 15
    assert config.request.endpoint == "/weather/2020"
    assert config.request.headers["Authorization"] == "Bearer secret123"
    assert config.mapping.files[0].source_path == "weather.csv"
    assert config.mapping.files[0].metadata_key == "weather"

def test_load_remote_config_missing_placeholder_raises() -> None:
    config_data = {
        "name": "test_service",
        "server": {"base_url": "https://example.com"},
        "request": {"endpoint": "/data/${MISSING_KEY}", "method": "GET"},
        "mapping": {"type": "direct_file", "files": []},
    }
    with pytest.raises(RemoteConfigValidationError, match="MISSING_KEY"):
        load_remote_config(config_data, param_overrides={})

def test_load_remote_config_from_file(tmp_path: Path) -> None:
    cfg_file = tmp_path / "remote.json"
    cfg_file.write_text(
        json.dumps({
            "name": "file_service",
            "server": {"base_url": "http://example.com"},
            "request": {"endpoint": "/data"},
            "mapping": {"type": "direct_file", "files": []},
        }),
        encoding="utf-8",
    )
    config = load_remote_config(cfg_file)
    assert config.name == "file_service"
    assert config.server.base_url == "http://example.com"

def test_load_remote_config_file_not_found(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist.json"
    with pytest.raises(RemoteConfigValidationError, match="not found"):
        load_remote_config(non_existent)

def test_domain_exceptions_hierarchy() -> None:
    for exc in (
        RemoteConfigValidationError,
        RemoteDataHttpError,
        RemoteDataConnectionError,
        ArchiveExtractionError,
        ArchiveSecurityError,
        ArchiveMappingError,
    ):
        assert issubclass(exc, RemoteAdapterError)
