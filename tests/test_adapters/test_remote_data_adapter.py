from io import BytesIO
from pathlib import Path
import zipfile
import pytest
from pytest_mock import MockerFixture

from RUFAS.adapters import RemoteDataAdapter, RemoteFetchResult
from RUFAS.adapters.archive_handler import ArchiveHandler
from RUFAS.adapters.http_client import HttpClient


def _make_zip(files: dict[str, str]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_remote_data_adapter_fetch_and_cache(tmp_path: Path, mocker: MockerFixture) -> None:
    zip_bytes = _make_zip({"weather.csv": "year,jday,precip\n2020,1,0.0"})
    mocker.patch("RUFAS.adapters.http_client.HttpClient.execute", return_value=zip_bytes)

    config_dict = {
        "name": "weather_test",
        "server": {"base_url": "https://api.example.com"},
        "request": {"endpoint": "/weather", "method": "GET"},
        "cache": {"enabled": True, "directory": str(tmp_path / "cache")},
        "mapping": {
            "type": "archive",
            "archive_format": "zip",
            "files": [
                {
                    "source_path": "weather.csv",
                    "destination_path": str(tmp_path / "inputs" / "weather.csv"),
                    "metadata_key": "weather",
                }
            ],
        },
    }

    adapter = RemoteDataAdapter()
    result = adapter.prepare_data(config_dict, base_dir=tmp_path)
    assert isinstance(result, RemoteFetchResult)
    assert result.from_cache is False
    dest = tmp_path / "inputs" / "weather.csv"
    assert result.extracted_files["weather"] == dest
    assert dest.is_file()
    assert dest.read_text() == "year,jday,precip\n2020,1,0.0"

    # Second invocation should be a cache hit (short-circuit because destinations are present)
    mock_exec = mocker.patch("RUFAS.adapters.http_client.HttpClient.execute")
    result2 = adapter.prepare_data(config_dict, base_dir=tmp_path)
    assert result2.from_cache is True
    assert result2.extracted_files["weather"] == dest
    mock_exec.assert_not_called()


def test_remote_data_adapter_payload_cached_but_destinations_missing(tmp_path: Path, mocker: MockerFixture) -> None:
    zip_bytes = _make_zip({"weather.csv": "year,jday,precip\n2020,1,0.0"})
    mocker.patch("RUFAS.adapters.http_client.HttpClient.execute", return_value=zip_bytes)

    dest = tmp_path / "inputs" / "weather.csv"
    config_dict = {
        "name": "weather_reunpack_test",
        "server": {"base_url": "https://api.example.com"},
        "request": {"endpoint": "/weather", "method": "GET"},
        "cache": {"enabled": True, "directory": str(tmp_path / "cache")},
        "mapping": {
            "type": "archive",
            "archive_format": "zip",
            "files": [
                {
                    "source_path": "weather.csv",
                    "destination_path": str(dest),
                    "metadata_key": "weather",
                }
            ],
        },
    }

    adapter = RemoteDataAdapter()
    # 1. Fetch & store in cache
    result1 = adapter.prepare_data(config_dict, base_dir=tmp_path)
    assert result1.from_cache is False
    assert dest.is_file()

    # 2. Delete destination file, keep cache intact
    dest.unlink()
    assert not dest.exists()

    mock_exec = mocker.patch("RUFAS.adapters.http_client.HttpClient.execute")
    mock_log = mocker.spy(adapter.output_manager, "add_log")
    # 3. Should read from cached payload without calling HTTP, unpack, and return from_cache=True
    result2 = adapter.prepare_data(config_dict, base_dir=tmp_path)
    assert result2.from_cache is True
    assert dest.is_file()
    mock_exec.assert_not_called()
    assert any(call[0][0] == "RemoteDataAdapter Re-unpacking Cache" for call in mock_log.call_args_list)



def test_remote_data_adapter_force_refresh(tmp_path: Path, mocker: MockerFixture) -> None:
    zip_bytes = _make_zip({"weather.csv": "year,jday,precip\n2020,1,0.0"})
    mock_exec = mocker.patch("RUFAS.adapters.http_client.HttpClient.execute", return_value=zip_bytes)

    config_dict = {
        "name": "refresh_test",
        "server": {"base_url": "https://api.example.com"},
        "request": {"endpoint": "/weather", "method": "GET"},
        "cache": {"enabled": True, "directory": str(tmp_path / "cache")},
        "mapping": {
            "type": "archive",
            "archive_format": "zip",
            "files": [
                {
                    "source_path": "weather.csv",
                    "destination_path": str(tmp_path / "weather.csv"),
                }
            ],
        },
    }

    adapter = RemoteDataAdapter()
    result1 = adapter.prepare_data(config_dict, base_dir=tmp_path)
    assert result1.from_cache is False
    assert mock_exec.call_count == 1

    # Call with force_refresh=True
    result2 = adapter.prepare_data(config_dict, force_refresh=True, base_dir=tmp_path)
    assert result2.from_cache is False
    assert mock_exec.call_count == 2


def test_remote_data_adapter_scenario_metadata(tmp_path: Path, mocker: MockerFixture) -> None:
    zip_bytes = _make_zip({"meta.json": '{"scenario": "A"}'})
    mocker.patch("RUFAS.adapters.http_client.HttpClient.execute", return_value=zip_bytes)

    config_dict = {
        "name": "meta_test",
        "server": {"base_url": "https://api.example.com"},
        "request": {"endpoint": "/data", "method": "GET"},
        "cache": {"enabled": True, "directory": str(tmp_path / "cache")},
        "mapping": {
            "type": "archive",
            "archive_format": "zip",
            "scenario_metadata": "custom_meta.json",
            "files": [
                {
                    "source_path": "meta.json",
                    "destination_path": "unpacked_meta.json",
                }
            ],
        },
    }

    adapter = RemoteDataAdapter()
    result = adapter.prepare_data(config_dict, base_dir=tmp_path)
    expected_meta = tmp_path / "custom_meta.json"
    assert result.scenario_metadata_path == expected_meta

    # On cache hit, scenario_metadata_path should still be preserved
    result_cached = adapter.prepare_data(config_dict, base_dir=tmp_path)
    assert result_cached.from_cache is True
    assert result_cached.scenario_metadata_path == expected_meta


def test_remote_data_adapter_direct_file(tmp_path: Path, mocker: MockerFixture) -> None:
    raw_csv = b"col1,col2\n10,20\n"
    mocker.patch("RUFAS.adapters.http_client.HttpClient.execute", return_value=raw_csv)

    dest = tmp_path / "data" / "direct.csv"
    config_dict = {
        "name": "direct_test",
        "server": {"base_url": "https://api.example.com"},
        "request": {"endpoint": "/direct.csv", "method": "GET"},
        "cache": {"enabled": False},
        "mapping": {
            "type": "direct_file",
            "files": [
                {
                    "source_path": "direct.csv",
                    "destination_path": str(dest),
                    "metadata_key": "my_csv",
                }
            ],
        },
    }

    adapter = RemoteDataAdapter()
    result = adapter.prepare_data(config_dict, base_dir=tmp_path)
    assert result.from_cache is False
    assert result.extracted_files["my_csv"] == dest
    assert dest.read_bytes() == raw_csv


def test_remote_data_adapter_parameter_overrides(tmp_path: Path, mocker: MockerFixture) -> None:
    zip_bytes = _make_zip({"data.txt": "hello"})
    mock_exec = mocker.patch("RUFAS.adapters.http_client.HttpClient.execute", return_value=zip_bytes)

    config_dict = {
        "name": "param_test",
        "server": {"base_url": "https://api.example.com"},
        "request": {"endpoint": "/station/${STATION_ID}", "method": "GET"},
        "cache": {"enabled": False},
        "mapping": {
            "type": "archive",
            "archive_format": "zip",
            "files": [{"source_path": "data.txt", "destination_path": "out.txt"}],
        },
    }

    adapter = RemoteDataAdapter()
    result = adapter.prepare_data(config_dict, param_overrides={"STATION_ID": "USW00014839"}, base_dir=tmp_path)
    assert result.extracted_files["data.txt"] == tmp_path / "out.txt"
    server_arg, request_arg = mock_exec.call_args[0]
    assert request_arg.endpoint == "/station/USW00014839"


def test_remote_data_adapter_dependency_injection(tmp_path: Path) -> None:
    mock_client = HttpClient()
    mock_handler = ArchiveHandler()
    adapter = RemoteDataAdapter(http_client=mock_client, archive_handler=mock_handler)
    assert adapter.http_client is mock_client
    assert adapter.archive_handler is mock_handler
