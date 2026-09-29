from pathlib import Path
import pytest
from RUFAS.adapters.cache_manager import CacheManager
from RUFAS.adapters.schema import CacheConfig, FileMapping, RequestConfig, ServerConfig


def test_cache_fingerprint_deterministic() -> None:
    cm = CacheManager()
    server = ServerConfig(base_url="https://api.example.com")
    req1 = RequestConfig(endpoint="/data", method="GET", params={"a": "1", "b": "2"})
    req2 = RequestConfig(endpoint="/data", method="GET", params={"b": "2", "a": "1"})
    assert cm.compute_key(server, req1) == cm.compute_key(server, req2)


def test_cache_fingerprint_headers_and_body_deterministic() -> None:
    cm = CacheManager()
    server = ServerConfig(base_url="https://api.example.com/")
    req1 = RequestConfig(
        endpoint="data",
        method="post",
        headers={"X-Custom": "val", "Authorization": "Bearer 123"},
        body={"z": 10, "a": 20},
    )
    req2 = RequestConfig(
        endpoint="/data",
        method="POST",
        headers={"Authorization": "Bearer 123", "X-Custom": "val"},
        body={"a": 20, "z": 10},
    )
    assert cm.compute_key(server, req1) == cm.compute_key(server, req2)


def test_cache_fingerprint_different_inputs() -> None:
    cm = CacheManager()
    server1 = ServerConfig(base_url="https://api1.example.com")
    server2 = ServerConfig(base_url="https://api2.example.com")
    req1 = RequestConfig(endpoint="/data", method="GET")
    req2 = RequestConfig(endpoint="/other", method="GET")
    assert cm.compute_key(server1, req1) != cm.compute_key(server2, req1)
    assert cm.compute_key(server1, req1) != cm.compute_key(server1, req2)


def test_cache_store_and_retrieve(tmp_path: Path) -> None:
    cache_config = CacheConfig(enabled=True, directory=str(tmp_path / "cache"))
    cm = CacheManager(cache_config=cache_config)
    key = "test_key_123"
    assert cm.get_cached_data(key) is None

    stored_path = cm.store(key, b"raw_download_payload")
    assert stored_path.is_file()
    assert stored_path.name == "payload.bin"

    cached = cm.get_cached_data(key)
    assert cached == b"raw_download_payload"


def test_cache_disabled(tmp_path: Path) -> None:
    cache_config = CacheConfig(enabled=False, directory=str(tmp_path / "cache"))
    cm = CacheManager(cache_config=cache_config)
    key = "test_disabled_key"

    # Store file directly on disk to test disabled check
    payload_file = tmp_path / "cache" / key / "payload.bin"
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_bytes(b"data")

    assert cm.get_cached_data(key) is None

    dest_file = tmp_path / "out.csv"
    dest_file.write_text("content")
    mapping = [FileMapping(source_path="out.csv", destination_path=str(dest_file))]
    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is False


def test_cache_force_refresh(tmp_path: Path) -> None:
    cache_config = CacheConfig(enabled=True, directory=str(tmp_path / "cache"), force_refresh=True)
    cm = CacheManager(cache_config=cache_config)
    key = "test_refresh_key"
    cm.store(key, b"raw_download_payload")

    dest_file = tmp_path / "out.csv"
    dest_file.write_text("content")
    mapping = [FileMapping(source_path="out.csv", destination_path=str(dest_file))]

    # Even though payload and dest exist, force_refresh must return False and get_cached_data must return None
    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is False
    assert cm.get_cached_data(key) is None


def test_cache_destination_check(tmp_path: Path) -> None:
    cache_config = CacheConfig(enabled=True, directory=str(tmp_path / "cache"))
    cm = CacheManager(cache_config=cache_config)
    key = "test_key_abc"
    cm.store(key, b"raw_download_payload")

    dest_file = tmp_path / "data" / "weather.csv"
    mapping = [FileMapping(source_path="weather.csv", destination_path=str(dest_file))]

    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is False
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    dest_file.write_text("dummy")
    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is True


def test_cache_destination_check_missing_payload(tmp_path: Path) -> None:
    cache_config = CacheConfig(enabled=True, directory=str(tmp_path / "cache"))
    cm = CacheManager(cache_config=cache_config)
    key = "test_key_no_payload"

    dest_file = tmp_path / "data" / "weather.csv"
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    dest_file.write_text("dummy")
    mapping = [FileMapping(source_path="weather.csv", destination_path=str(dest_file))]

    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is False


def test_cache_destination_check_relative_path(tmp_path: Path) -> None:
    cache_config = CacheConfig(enabled=True, directory=str(tmp_path / "cache"))
    cm = CacheManager(cache_config=cache_config)
    key = "test_key_rel"
    cm.store(key, b"raw_download_payload")

    rel_dest = "rel_data/soil.csv"
    mapping = [FileMapping(source_path="soil.csv", destination_path=rel_dest)]

    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is False
    full_dest = tmp_path / rel_dest
    full_dest.parent.mkdir(parents=True, exist_ok=True)
    full_dest.write_text("soil_data")
    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is True


def test_cache_destination_multiple_files(tmp_path: Path) -> None:
    cache_config = CacheConfig(enabled=True, directory=str(tmp_path / "cache"))
    cm = CacheManager(cache_config=cache_config)
    key = "test_key_multi"
    cm.store(key, b"payload")

    f1 = tmp_path / "f1.csv"
    f2 = tmp_path / "f2.csv"
    mapping = [
        FileMapping(source_path="f1.csv", destination_path=str(f1)),
        FileMapping(source_path="f2.csv", destination_path=str(f2)),
    ]

    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is False
    f1.write_text("data1")
    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is False
    f2.write_text("data2")
    assert cm.are_destinations_present(key, mapping, base_dir=tmp_path) is True


def test_cache_is_cached_alias(tmp_path: Path) -> None:
    cache_config = CacheConfig(enabled=True, directory=str(tmp_path / "cache"))
    cm = CacheManager(cache_config=cache_config)
    key = "test_key_alias"
    cm.store(key, b"payload")

    dest = tmp_path / "file.csv"
    mapping = [FileMapping(source_path="file.csv", destination_path=str(dest))]
    assert cm.is_cached(key, mapping, base_dir=tmp_path) is False
    dest.write_text("ok")
    assert cm.is_cached(key, mapping, base_dir=tmp_path) is True


def test_cache_invalid_key_traversal(tmp_path: Path) -> None:
    cm = CacheManager()
    with pytest.raises(ValueError, match="Invalid cache key"):
        cm.store("../evil_key", b"data")
    with pytest.raises(ValueError, match="Invalid cache key"):
        cm.get_cached_data("/absolute/key")


def test_cache_invalid_key_empty_or_dot() -> None:
    cm = CacheManager()
    with pytest.raises(ValueError, match="Invalid cache key"):
        cm.get_cached_data("")
    with pytest.raises(ValueError, match="Invalid cache key"):
        cm.get_cached_data(".")
    with pytest.raises(ValueError, match="Invalid cache key"):
        cm.store("", b"data")
    with pytest.raises(ValueError, match="Invalid cache key"):
        cm.store(".", b"data")

