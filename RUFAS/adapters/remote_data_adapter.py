"""High-level facade orchestrating data fetching, caching, and archive mapping."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from RUFAS.adapters.archive_handler import ArchiveHandler
from RUFAS.adapters.cache_manager import CacheManager
from RUFAS.adapters.http_client import HttpClient
from RUFAS.adapters.schema import RemoteConfig, load_remote_config
from RUFAS.output_manager import OutputManager


@dataclass
class RemoteFetchResult:
    """Result returned by RemoteDataAdapter.prepare_data."""

    extracted_files: dict[str, Path]
    scenario_metadata_path: Path | None = None
    from_cache: bool = False


class RemoteDataAdapter:
    """High-level facade orchestrating data fetching, caching, and archive mapping."""

    def __init__(
        self,
        http_client: HttpClient | None = None,
        archive_handler: ArchiveHandler | None = None,
    ) -> None:
        self.http_client = http_client or HttpClient()
        self.archive_handler = archive_handler or ArchiveHandler()
        self.output_manager = OutputManager()

    def prepare_data(
        self,
        config_input: dict[str, Any] | Path | str,
        param_overrides: dict[str, str] | None = None,
        force_refresh: bool = False,
        base_dir: Path | None = None,
    ) -> RemoteFetchResult:
        """Load remote configuration, check cache, download payload, and map extracted files.

        Args:
            config_input: Remote configuration as a dictionary, file Path, or JSON/YAML string.
            param_overrides: Dictionary of parameter key-value pairs to substitute placeholders.
            force_refresh: Whether to bypass cache and force a new fetch.
            base_dir: Base directory to resolve relative destination paths against.

        Returns:
            RemoteFetchResult containing mapped file paths, scenario metadata path, and cache hit flag.
        """
        root_dir = Path(base_dir) if base_dir is not None else Path.cwd()
        config: RemoteConfig = load_remote_config(config_input, param_overrides)
        if force_refresh:
            config.cache.force_refresh = True

        cache_mgr = CacheManager(config.cache)
        cache_key = cache_mgr.compute_key(config.server, config.request)
        info_map = {"class": self.__class__.__name__, "function": self.prepare_data.__name__}

        scenario_meta: Path | None = None
        if config.mapping.scenario_metadata:
            meta_dest = Path(config.mapping.scenario_metadata)
            if not meta_dest.is_absolute():
                meta_dest = root_dir / meta_dest
            scenario_meta = meta_dest

        if cache_mgr.are_destinations_present(cache_key, config.mapping.files, root_dir):
            self.output_manager.add_log(
                "RemoteDataAdapter Cache Hit",
                f"Reusing cached artifacts for remote source '{config.name}' (key: {cache_key[:12]}).",
                info_map,
            )
            resolved: dict[str, Path] = {}
            for f in config.mapping.files:
                dest = Path(f.destination_path)
                if not dest.is_absolute():
                    dest = root_dir / dest
                key = f.metadata_key or f.source_path
                resolved[key] = dest
            return RemoteFetchResult(
                extracted_files=resolved,
                scenario_metadata_path=scenario_meta,
                from_cache=True,
            )

        cached_payload = cache_mgr.get_cached_data(cache_key)
        if cached_payload is not None and not config.cache.force_refresh:
            self.output_manager.add_log(
                "RemoteDataAdapter Re-unpacking Cache",
                f"Re-unpacking cached payload for '{config.name}' (key: {cache_key[:12]}).",
                info_map,
            )
            payload = cached_payload
            from_cache = True
        else:
            self.output_manager.add_log(
                "RemoteDataAdapter Fetching",
                f"Fetching data from '{config.server.base_url}{config.request.endpoint}' via {config.request.method}...",
                info_map,
            )
            payload = self.http_client.execute(config.server, config.request)
            if config.cache.enabled:
                cache_mgr.store(cache_key, payload)
            from_cache = False

        resolved_files = self.archive_handler.unpack_and_map(payload, config.mapping, root_dir)

        return RemoteFetchResult(
            extracted_files=resolved_files,
            scenario_metadata_path=scenario_meta,
            from_cache=from_cache,
        )
