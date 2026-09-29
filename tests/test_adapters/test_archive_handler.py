from io import BytesIO
from pathlib import Path
import tarfile
import zipfile
import pytest

from RUFAS.adapters.archive_handler import ArchiveHandler
from RUFAS.adapters.exceptions import (
    ArchiveExtractionError,
    ArchiveMappingError,
    ArchiveSecurityError,
)
from RUFAS.adapters.schema import FileMapping, MappingConfig


def create_sample_zip(files: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def create_sample_tar(files: dict[str, str], mode: str = "w") -> bytes:
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode=mode) as tf:
        for name, content in files.items():
            content_bytes = content.encode("utf-8")
            ti = tarfile.TarInfo(name=name)
            ti.size = len(content_bytes)
            tf.addfile(ti, BytesIO(content_bytes))
    return buffer.getvalue()


def test_extract_zip_valid_mapping(tmp_path: Path) -> None:
    zip_bytes = create_sample_zip({"data/weather.csv": "year,jday\n2020,1"})
    mapping = MappingConfig(
        type="archive",
        archive_format="zip",
        files=[
            FileMapping(
                source_path="data/weather.csv",
                destination_path=str(tmp_path / "out_weather.csv"),
                metadata_key="weather",
            )
        ],
    )
    handler = ArchiveHandler()
    result = handler.unpack_and_map(zip_bytes, mapping, base_dir=tmp_path)
    dest_path = tmp_path / "out_weather.csv"
    assert result["weather"] == dest_path
    assert dest_path.is_file()
    assert dest_path.read_text(encoding="utf-8") == "year,jday\n2020,1"


def test_extract_zip_missing_source_file_raises(tmp_path: Path) -> None:
    zip_bytes = create_sample_zip({"data/other.csv": "col1\nval1"})
    mapping = MappingConfig(
        type="archive",
        archive_format="zip",
        files=[
            FileMapping(
                source_path="data/missing.csv",
                destination_path=str(tmp_path / "out.csv"),
                metadata_key="test",
            )
        ],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveMappingError, match="missing.csv"):
        handler.unpack_and_map(zip_bytes, mapping, base_dir=tmp_path)


def test_extract_zip_path_traversal_blocked(tmp_path: Path) -> None:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("../evil.txt", "malicious payload")
    zip_bytes = buffer.getvalue()

    mapping = MappingConfig(
        type="archive",
        archive_format="zip",
        files=[FileMapping(source_path="../evil.txt", destination_path=str(tmp_path / "evil.txt"))],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveSecurityError, match="traversal"):
        handler.unpack_and_map(zip_bytes, mapping, base_dir=tmp_path)


def test_extract_zip_relative_dest_path(tmp_path: Path) -> None:
    zip_bytes = create_sample_zip({"data/file.txt": "relative dest test"})
    mapping = MappingConfig(
        type="archive",
        archive_format="zip",
        files=[
            FileMapping(
                source_path="data/file.txt",
                destination_path="nested/dir/file.txt",
            )
        ],
    )
    handler = ArchiveHandler()
    result = handler.unpack_and_map(zip_bytes, mapping, base_dir=tmp_path)
    expected_path = tmp_path / "nested/dir/file.txt"
    assert result["data/file.txt"] == expected_path
    assert expected_path.is_file()
    assert expected_path.read_text(encoding="utf-8") == "relative dest test"


def test_extract_zip_corrupt_raises(tmp_path: Path) -> None:
    corrupt_data = b"not a valid zip file content"
    mapping = MappingConfig(
        type="archive",
        archive_format="zip",
        files=[FileMapping(source_path="some.txt", destination_path="dest.txt")],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveExtractionError, match="Corrupted or invalid ZIP archive"):
        handler.unpack_and_map(corrupt_data, mapping, base_dir=tmp_path)


def test_extract_tar_valid_mapping(tmp_path: Path) -> None:
    tar_bytes = create_sample_tar({"sample.csv": "colA,colB\n1,2"}, mode="w")
    mapping = MappingConfig(
        type="archive",
        archive_format="tar",
        files=[
            FileMapping(
                source_path="sample.csv",
                destination_path=str(tmp_path / "extracted.csv"),
                metadata_key="sample_key",
            )
        ],
    )
    handler = ArchiveHandler()
    result = handler.unpack_and_map(tar_bytes, mapping, base_dir=tmp_path)
    dest_path = tmp_path / "extracted.csv"
    assert result["sample_key"] == dest_path
    assert dest_path.is_file()
    assert dest_path.read_text(encoding="utf-8") == "colA,colB\n1,2"


def test_extract_tar_gz_valid_mapping(tmp_path: Path) -> None:
    tar_bytes = create_sample_tar({"nested/weather.json": '{"temp": 22}'}, mode="w:gz")
    mapping = MappingConfig(
        type="archive",
        archive_format="tar.gz",
        files=[
            FileMapping(
                source_path="nested/weather.json",
                destination_path="out/weather.json",
                metadata_key="weather_json",
            )
        ],
    )
    handler = ArchiveHandler()
    result = handler.unpack_and_map(tar_bytes, mapping, base_dir=tmp_path)
    expected = tmp_path / "out/weather.json"
    assert result["weather_json"] == expected
    assert expected.read_text(encoding="utf-8") == '{"temp": 22}'


def test_extract_tar_bz2_valid_mapping(tmp_path: Path) -> None:
    tar_bytes = create_sample_tar({"info.txt": "bzip2 content"}, mode="w:bz2")
    mapping = MappingConfig(
        type="archive",
        archive_format="tar.bz2",
        files=[
            FileMapping(
                source_path="info.txt",
                destination_path="info_out.txt",
            )
        ],
    )
    handler = ArchiveHandler()
    result = handler.unpack_and_map(tar_bytes, mapping, base_dir=tmp_path)
    assert result["info.txt"] == tmp_path / "info_out.txt"
    assert (tmp_path / "info_out.txt").read_text(encoding="utf-8") == "bzip2 content"


def test_extract_tar_missing_source_file_raises(tmp_path: Path) -> None:
    tar_bytes = create_sample_tar({"exists.txt": "ok"})
    mapping = MappingConfig(
        type="archive",
        archive_format="tar",
        files=[FileMapping(source_path="not_found.txt", destination_path="out.txt")],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveMappingError, match="not_found.txt"):
        handler.unpack_and_map(tar_bytes, mapping, base_dir=tmp_path)


def test_extract_tar_path_traversal_blocked(tmp_path: Path) -> None:
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tf:
        payload = b"malicious"
        ti = tarfile.TarInfo(name="../escape.txt")
        ti.size = len(payload)
        tf.addfile(ti, BytesIO(payload))
    tar_bytes = buffer.getvalue()

    mapping = MappingConfig(
        type="archive",
        archive_format="tar",
        files=[FileMapping(source_path="../escape.txt", destination_path="escape.txt")],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveSecurityError, match="traversal"):
        handler.unpack_and_map(tar_bytes, mapping, base_dir=tmp_path)


def test_extract_tar_corrupt_raises(tmp_path: Path) -> None:
    corrupt_data = b"definitely not tar data"
    mapping = MappingConfig(
        type="archive",
        archive_format="tar",
        files=[FileMapping(source_path="foo.txt", destination_path="bar.txt")],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveExtractionError, match="Corrupted or invalid tar archive"):
        handler.unpack_and_map(corrupt_data, mapping, base_dir=tmp_path)


def test_extract_direct_file_valid_mapping(tmp_path: Path) -> None:
    file_bytes = b"single direct file content"
    mapping = MappingConfig(
        type="direct_file",
        files=[
            FileMapping(
                source_path="raw_download",
                destination_path=str(tmp_path / "direct/output.bin"),
                metadata_key="direct_file_key",
            )
        ],
    )
    handler = ArchiveHandler()
    result = handler.unpack_and_map(file_bytes, mapping, base_dir=tmp_path)
    dest_path = tmp_path / "direct/output.bin"
    assert result["direct_file_key"] == dest_path
    assert dest_path.is_file()
    assert dest_path.read_bytes() == file_bytes


def test_extract_direct_file_relative_path(tmp_path: Path) -> None:
    file_bytes = b"relative payload"
    mapping = MappingConfig(
        type="direct_file",
        files=[
            FileMapping(
                source_path="data.csv",
                destination_path="subfolder/data.csv",
            )
        ],
    )
    handler = ArchiveHandler()
    result = handler.unpack_and_map(file_bytes, mapping, base_dir=tmp_path)
    dest_path = tmp_path / "subfolder/data.csv"
    assert result["data.csv"] == dest_path
    assert dest_path.read_bytes() == file_bytes


def test_extract_unsupported_mapping_type_raises(tmp_path: Path) -> None:
    mapping = MappingConfig(type="unsupported_type")
    handler = ArchiveHandler()
    with pytest.raises(ArchiveExtractionError, match="Unsupported mapping type"):
        handler.unpack_and_map(b"data", mapping, base_dir=tmp_path)


def test_extract_unsupported_archive_format_raises(tmp_path: Path) -> None:
    mapping = MappingConfig(type="archive", archive_format="7z")
    handler = ArchiveHandler()
    with pytest.raises(ArchiveExtractionError, match="Unsupported archive format"):
        handler.unpack_and_map(b"data", mapping, base_dir=tmp_path)


def test_extract_tar_directory_member_raises(tmp_path: Path) -> None:
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tf:
        ti = tarfile.TarInfo(name="adir")
        ti.type = tarfile.DIRTYPE
        tf.addfile(ti)
    tar_bytes = buffer.getvalue()

    mapping = MappingConfig(
        type="archive",
        archive_format="tar",
        files=[FileMapping(source_path="adir", destination_path="adir")],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveExtractionError, match="Cannot extract member 'adir' as regular file"):
        handler.unpack_and_map(tar_bytes, mapping, base_dir=tmp_path)


def test_extract_tar_broken_symlink_raises(tmp_path: Path) -> None:
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tf:
        ti = tarfile.TarInfo(name="broken_symlink.csv")
        ti.type = tarfile.SYMTYPE
        ti.linkname = "non_existent_target.csv"
        tf.addfile(ti)
    tar_bytes = buffer.getvalue()

    mapping = MappingConfig(
        type="archive",
        archive_format="tar",
        files=[FileMapping(source_path="broken_symlink.csv", destination_path="out.csv")],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveExtractionError):
        handler.unpack_and_map(tar_bytes, mapping, base_dir=tmp_path)


def test_extract_zip_backslash_traversal_blocked(tmp_path: Path) -> None:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("..\\evil.txt", "malicious payload")
    zip_bytes = buffer.getvalue()

    mapping = MappingConfig(
        type="archive",
        archive_format="zip",
        files=[FileMapping(source_path="..\\evil.txt", destination_path=str(tmp_path / "evil.txt"))],
    )
    handler = ArchiveHandler()
    with pytest.raises(ArchiveSecurityError, match="traversal"):
        handler.unpack_and_map(zip_bytes, mapping, base_dir=tmp_path)

