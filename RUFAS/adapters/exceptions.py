"""Domain exceptions for RuFaS remote data adapters."""

class RemoteAdapterError(Exception):
    """Base exception for all remote adapter errors."""

class RemoteConfigValidationError(RemoteAdapterError):
    """Raised when configuration validation or parameter interpolation fails."""

class RemoteDataHttpError(RemoteAdapterError):
    """Raised when remote server returns a 4xx or 5xx HTTP status."""

class RemoteDataConnectionError(RemoteAdapterError):
    """Raised when network connection, timeout, or DNS resolution fails."""

class ArchiveExtractionError(RemoteAdapterError):
    """Raised when archive is corrupt or cannot be read."""

class ArchiveSecurityError(RemoteAdapterError):
    """Raised when archive contains path traversal sequences."""

class ArchiveMappingError(RemoteAdapterError):
    """Raised when mapped file is not found inside the archive."""
