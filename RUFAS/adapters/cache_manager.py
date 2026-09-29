from __future__ import annotations

import hashlib
import json
from pathlib import Path
from RUFAS.adapters.schema import CacheConfig, FileMapping, RequestConfig, ServerConfig


class CacheManager:
    """Manages request fingerprinting and cached payload persistence."""

    def __init__(self, cache_config: CacheConfig | None = None) -> None:
        self.config = cache_config or CacheConfig()

    def _validate_key(self, key: str) -> None:
        if not key or key == ".":
            raise ValueError(f"Invalid cache key: '{key}'")
        normalized = key.replace("\\", "/")
        if ".." in Path(normalized).parts or Path(normalized).is_absolute() or "/" in normalized:
            raise ValueError(f"Invalid cache key: '{key}'")

    def compute_key(self, server: ServerConfig, request: RequestConfig) -> str:
        canonical = [
            request.method.upper(),
            server.base_url.rstrip("/"),
            request.endpoint.lstrip("/"),
            sorted(request.headers.items()),
            sorted(request.params.items()),
            json.dumps(request.body, sort_keys=True) if isinstance(request.body, (dict, list)) else str(request.body),
        ]
        serialized = repr(canonical).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def _get_cache_dir(self, key: str) -> Path:
        self._validate_key(key)
        return Path(self.config.directory) / key

    def store(self, key: str, data: bytes) -> Path:
        cache_dir = self._get_cache_dir(key)
        cache_dir.mkdir(parents=True, exist_ok=True)
        payload_file = cache_dir / "payload.bin"
        payload_file.write_bytes(data)
        return payload_file

    def get_cached_data(self, key: str) -> bytes | None:
        if not self.config.enabled or self.config.force_refresh:
            return None
        payload_file = self._get_cache_dir(key) / "payload.bin"
        if payload_file.is_file():
            return payload_file.read_bytes()
        return None

    def are_destinations_present(self, key: str, files: list[FileMapping], base_dir: Path) -> bool:
        if not self.config.enabled or self.config.force_refresh:
            return False
        if not (self._get_cache_dir(key) / "payload.bin").is_file():
            return False
        base = Path(base_dir)
        for f in files:
            dest = Path(f.destination_path)
            if not dest.is_absolute():
                dest = base / dest
            if not dest.is_file():
                return False
        return True

    def is_cached(self, key: str, files: list[FileMapping], base_dir: Path) -> bool:
        """Alias for are_destinations_present to satisfy interface contract."""
        return self.are_destinations_present(key, files, base_dir)
