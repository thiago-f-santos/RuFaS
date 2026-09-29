from http.server import HTTPServer, SimpleHTTPRequestHandler
from io import BytesIO
import json
from pathlib import Path
import threading
import zipfile
import pytest
from RUFAS.task_manager import TaskManager


@pytest.fixture(autouse=True)
def cleanup_runtime_metadata() -> None:
    """Cleans up any ephemeral runtime metadata files created during integration tests."""
    yield
    runtime_files = list(Path("input/metadata").glob(".runtime_*.json"))
    for f in runtime_files:
        try:
            f.unlink()
        except OSError:
            pass


class EphemeralZipServer:
    def __init__(self, zip_content: bytes):
        self.zip_content = zip_content
        handler_cls = self._make_handler()
        self.server = HTTPServer(("127.0.0.1", 0), handler_cls)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True

    def _make_handler(self):
        content = self.zip_content

        class ZipHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def log_message(self, format, *args):
                pass

        return ZipHandler

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def test_full_remote_weather_simulation_e2e(tmp_path: Path) -> None:
    # 1. Read real temperate weather CSV sample
    real_weather = Path("input/data/weather/example_temperate_weather.csv").read_text(encoding="utf-8")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("weather.csv", real_weather)
    zip_bytes = buf.getvalue()

    # 2. Start local HTTP server
    server = EphemeralZipServer(zip_bytes)
    server.start()
    try:
        remote_config = {
            "name": "e2e_weather_server",
            "server": {"base_url": f"http://127.0.0.1:{server.port}"},
            "request": {"endpoint": "/download", "method": "GET"},
            "cache": {"enabled": False},
            "mapping": {
                "type": "archive",
                "archive_format": "zip",
                "files": [
                    {
                        "source_path": "weather.csv",
                        "destination_path": str(tmp_path / "fetched_weather.csv"),
                        "metadata_key": "weather",
                    }
                ],
            },
        }
        cfg_path = tmp_path / "remote_config.json"
        cfg_path.write_text(json.dumps(remote_config), encoding="utf-8")

        tm = TaskManager()
        tm.start(
            metadata_path=Path("input/task_manager_metadata.json"),
            remote_config_path=cfg_path,
            output_directory=tmp_path / "output",
            logs_directory=tmp_path / "output" / "logs",
            suppress_log_files=False,
            clear_output_directory=True,
        )

        fetched_weather = tmp_path / "fetched_weather.csv"
        assert fetched_weather.is_file()
        assert fetched_weather.read_text(encoding="utf-8") == real_weather

        # RuFaS OutputManager dumps non-data pools to JSON: <prefix>_logs_<timestamp>.json
        log_files = list((tmp_path / "output" / "logs").glob("*logs*.json"))
        assert len(log_files) > 0 or (tmp_path / "output" / "logs" / "logs.txt").is_file()
    finally:
        server.stop()
