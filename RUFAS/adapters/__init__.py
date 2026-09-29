"""Adapter subsystem for external data fetching and integration."""

from RUFAS.adapters.exceptions import (
    ArchiveExtractionError,
    ArchiveMappingError,
    ArchiveSecurityError,
    RemoteAdapterError,
    RemoteConfigValidationError,
    RemoteDataConnectionError,
    RemoteDataHttpError,
)
from RUFAS.adapters.remote_data_adapter import RemoteDataAdapter, RemoteFetchResult
from RUFAS.adapters.schema import RemoteConfig, load_remote_config

__all__ = [
    "RemoteDataAdapter",
    "RemoteFetchResult",
    "RemoteConfig",
    "load_remote_config",
    "RemoteAdapterError",
    "RemoteConfigValidationError",
    "RemoteDataHttpError",
    "RemoteDataConnectionError",
    "ArchiveExtractionError",
    "ArchiveSecurityError",
    "ArchiveMappingError",
]
