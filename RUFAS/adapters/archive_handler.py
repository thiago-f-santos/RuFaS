"""Archive unpacker and security guard for remote data adapter subsystem."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tarfile
import zipfile

from RUFAS.adapters.exceptions import (
    ArchiveExtractionError,
    ArchiveMappingError,
    ArchiveSecurityError,
)
from RUFAS.adapters.schema import MappingConfig


class ArchiveHandler:
    """Extracts, validates, and maps archives or direct files to destination paths."""

    def unpack_and_map(
        self,
        data: bytes,
        mapping: MappingConfig,
        base_dir: Path,
    ) -> dict[str, Path]:
        """Unpack archive or direct file payload and map files to local destinations.

        Args:
            data: Raw downloaded bytes of archive or single file.
            mapping: MappingConfig defining archive format, type, and file mappings.
            base_dir: Base directory to resolve relative destination paths against.

        Returns:
            Dictionary mapping metadata keys (or source paths) to resolved Path objects.

        Raises:
            ArchiveSecurityError: If any path traversal attempt is detected.
            ArchiveExtractionError: If archive is invalid, corrupted, or unsupported.
            ArchiveMappingError: If a mapped source file is missing from archive.
        """
        resolved_files: dict[str, Path] = {}

        if mapping.type == "direct_file":
            for f in mapping.files:
                if ".." in Path(f.destination_path.replace("\\", "/")).parts:
                    raise ArchiveSecurityError(
                        f"Path traversal detected in destination path: '{f.destination_path}'"
                    )
                dest = Path(f.destination_path)
                if not dest.is_absolute():
                    dest = base_dir / dest
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                key = f.metadata_key or f.source_path
                resolved_files[key] = dest
            return resolved_files

        if mapping.type != "archive":
            raise ArchiveExtractionError(f"Unsupported mapping type: '{mapping.type}'")

        if mapping.archive_format == "zip":
            try:
                with zipfile.ZipFile(BytesIO(data)) as zf:
                    for name in zf.namelist():
                        if ".." in Path(name.replace("\\", "/")).parts:
                            raise ArchiveSecurityError(
                                f"Path traversal detected in archive entry: '{name}'"
                            )

                    available_names = set(zf.namelist())
                    for f in mapping.files:
                        source = f.source_path.lstrip("/").replace("\\", "/")
                        if ".." in Path(source).parts:
                            raise ArchiveSecurityError(
                                f"Path traversal detected in archive member: '{source}'"
                            )
                        if ".." in Path(f.destination_path.replace("\\", "/")).parts:
                            raise ArchiveSecurityError(
                                f"Path traversal detected in destination path: '{f.destination_path}'"
                            )
                        if source not in available_names:
                            raise ArchiveMappingError(
                                f"Archive does not contain mapped source file: '{source}'. "
                                f"Available members: {sorted(list(available_names))[:10]}"
                            )
                        dest = Path(f.destination_path)
                        if not dest.is_absolute():
                            dest = base_dir / dest
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(zf.read(source))
                        key = f.metadata_key or source
                        resolved_files[key] = dest
            except zipfile.BadZipFile as bzf:
                raise ArchiveExtractionError(f"Corrupted or invalid ZIP archive: {bzf}") from bzf

        elif mapping.archive_format.startswith("tar") or mapping.archive_format in ("tgz", "tbz", "txz"):
            mode = "r:*"
            if mapping.archive_format in ("tar.gz", "tgz"):
                mode = "r:gz"
            elif mapping.archive_format in ("tar.bz2", "tbz"):
                mode = "r:bz2"
            elif mapping.archive_format in ("tar.xz", "txz"):
                mode = "r:xz"
            elif mapping.archive_format == "tar":
                mode = "r:"

            try:
                with tarfile.open(fileobj=BytesIO(data), mode=mode) as tf:
                    members = tf.getmembers()
                    for m in members:
                        if ".." in Path(m.name.replace("\\", "/")).parts:
                            raise ArchiveSecurityError(
                                f"Path traversal detected in archive entry: '{m.name}'"
                            )

                    tar_names = {m.name: m for m in members}
                    for f in mapping.files:
                        source = f.source_path.lstrip("/").replace("\\", "/")
                        if ".." in Path(source).parts:
                            raise ArchiveSecurityError(
                                f"Path traversal detected in archive member: '{source}'"
                            )
                        if ".." in Path(f.destination_path.replace("\\", "/")).parts:
                            raise ArchiveSecurityError(
                                f"Path traversal detected in destination path: '{f.destination_path}'"
                            )
                        if source not in tar_names:
                            raise ArchiveMappingError(
                                f"Archive does not contain mapped source file: '{source}'."
                            )
                        member = tar_names[source]
                        if not member.isfile():
                            raise ArchiveExtractionError(
                                f"Cannot extract member '{source}' as regular file."
                            )
                        extracted_f = tf.extractfile(member)
                        if extracted_f is None:
                            raise ArchiveExtractionError(
                                f"Cannot extract member '{source}' as regular file."
                            )
                        dest = Path(f.destination_path)
                        if not dest.is_absolute():
                            dest = base_dir / dest
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(extracted_f.read())
                        key = f.metadata_key or source
                        resolved_files[key] = dest
            except (tarfile.TarError, KeyError) as te:
                raise ArchiveExtractionError(f"Corrupted or invalid tar archive: {te}") from te
        else:
            raise ArchiveExtractionError(f"Unsupported archive format: '{mapping.archive_format}'")

        return resolved_files
