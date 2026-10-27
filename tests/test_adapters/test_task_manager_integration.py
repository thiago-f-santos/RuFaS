import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from pytest_mock import MockerFixture
from RUFAS.adapters import RemoteFetchResult
from RUFAS.task_manager import TaskManager, TaskType


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


def test_task_manager_resolves_remote_source(tmp_path: Path, mocker: MockerFixture) -> None:
    scenario_meta = {
        "files": {
            "weather": {
                "path": "input/data/weather/default.csv",
                "type": "csv",
                "properties": "weather_properties",
                "remote_source": "config/remote_weather.json",
            }
        }
    }
    scenario_path = tmp_path / "scenario_metadata.json"
    scenario_path.write_text(json.dumps(scenario_meta), encoding="utf-8")

    task_def = {
        "tasks": [
            {
                "task_id": "test_run",
                "task_type": "INPUT_DATA_AUDIT",
                "args": {
                    "metadata_file_path": str(scenario_path),
                    "input_root": str(tmp_path),
                    "task_id": "test_run",
                    "output_prefix": "test",
                    "logs_directory": str(tmp_path / "logs"),
                    "suppress_log_files": True,
                    "export_input_data_to_csv": False,
                },
            }
        ]
    }
    task_def_path = tmp_path / "tasks.json"
    task_def_path.write_text(json.dumps(task_def), encoding="utf-8")

    tm_meta = {"tasks_properties": str(task_def_path)}
    tm_meta_path = tmp_path / "task_manager_metadata.json"
    tm_meta_path.write_text(json.dumps(tm_meta), encoding="utf-8")

    downloaded_weather = tmp_path / "weather_downloaded.csv"
    downloaded_weather.write_text("year,jday\n2020,1")

    mock_result = RemoteFetchResult(extracted_files={"weather": downloaded_weather})
    mocker.patch(
        "RUFAS.adapters.RemoteDataAdapter.prepare_data",
        return_value=mock_result,
    )
    mock_input_manager = mocker.patch("RUFAS.task_manager.InputManager", autospec=True)
    mock_im_instance = mock_input_manager.return_value
    mock_im_instance.start_data_processing.return_value = True

    tm = TaskManager()
    tm.start(metadata_path=tm_meta_path, suppress_log_files=True)

    # Check that InputManager was called with resolved runtime metadata
    called_path = mock_im_instance.start_data_processing.call_args[0][0]
    with open(called_path, "r", encoding="utf-8") as f:
        resolved_meta = json.load(f)
    assert resolved_meta["files"]["weather"]["path"] == str(downloaded_weather)


def test_task_manager_with_remote_config_cli_override(tmp_path: Path, mocker: MockerFixture) -> None:
    scenario_meta = {
        "files": {
            "weather": {
                "path": "input/data/weather/default.csv",
                "type": "csv",
                "properties": "weather_properties",
            }
        }
    }
    scenario_path = tmp_path / "scenario_metadata.json"
    scenario_path.write_text(json.dumps(scenario_meta), encoding="utf-8")

    task_def = {
        "tasks": [
            {
                "task_id": "cli_override_run",
                "task_type": "INPUT_DATA_AUDIT",
                "args": {
                    "metadata_file_path": str(scenario_path),
                    "input_root": str(tmp_path),
                    "task_id": "cli_override_run",
                    "output_prefix": "cli_test",
                    "logs_directory": str(tmp_path / "logs"),
                    "suppress_log_files": True,
                    "export_input_data_to_csv": False,
                },
            }
        ]
    }
    task_def_path = tmp_path / "tasks.json"
    task_def_path.write_text(json.dumps(task_def), encoding="utf-8")

    tm_meta = {"tasks_properties": str(task_def_path)}
    tm_meta_path = tmp_path / "task_manager_metadata.json"
    tm_meta_path.write_text(json.dumps(tm_meta), encoding="utf-8")

    cli_weather = tmp_path / "weather_from_cli.csv"
    cli_weather.write_text("year,jday\n2022,100")

    mock_prepare = mocker.patch(
        "RUFAS.adapters.RemoteDataAdapter.prepare_data",
        return_value=RemoteFetchResult(extracted_files={"weather": cli_weather}),
    )
    mock_input_manager = mocker.patch("RUFAS.task_manager.InputManager", autospec=True)
    mock_im_instance = mock_input_manager.return_value
    mock_im_instance.start_data_processing.return_value = True

    remote_cfg_path = tmp_path / "cli_remote_config.json"
    remote_cfg_path.write_text('{"name": "test"}', encoding="utf-8")

    tm = TaskManager()
    tm.start(
        metadata_path=tm_meta_path,
        remote_config_path=remote_cfg_path,
        remote_params={"YEAR": "2022"},
        force_fetch=True,
        suppress_log_files=True,
    )

    mock_prepare.assert_called_once_with(
        remote_cfg_path,
        param_overrides={"YEAR": "2022"},
        force_refresh=True,
    )

    called_path = mock_im_instance.start_data_processing.call_args[0][0]
    with open(called_path, "r", encoding="utf-8") as f:
        resolved_meta = json.load(f)
    assert resolved_meta["files"]["weather"]["path"] == str(cli_weather)


def test_task_manager_scenario_metadata_override(tmp_path: Path, mocker: MockerFixture) -> None:
    scenario_path = tmp_path / "scenario_metadata.json"
    scenario_path.write_text('{"files": {}}', encoding="utf-8")

    task_def = {
        "tasks": [
            {
                "task_id": "bundle_run",
                "task_type": "INPUT_DATA_AUDIT",
                "args": {
                    "metadata_file_path": str(scenario_path),
                    "input_root": str(tmp_path),
                    "task_id": "bundle_run",
                    "output_prefix": "bundle_test",
                    "logs_directory": str(tmp_path / "logs"),
                    "suppress_log_files": True,
                    "export_input_data_to_csv": False,
                },
            }
        ]
    }
    task_def_path = tmp_path / "tasks.json"
    task_def_path.write_text(json.dumps(task_def), encoding="utf-8")

    tm_meta = {"tasks_properties": str(task_def_path)}
    tm_meta_path = tmp_path / "task_manager_metadata.json"
    tm_meta_path.write_text(json.dumps(tm_meta), encoding="utf-8")

    downloaded_bundle_meta = tmp_path / "downloaded_bundle_scenario.json"
    downloaded_bundle_meta.write_text('{"bundle": true, "files": {}}', encoding="utf-8")

    mocker.patch(
        "RUFAS.adapters.RemoteDataAdapter.prepare_data",
        return_value=RemoteFetchResult(
            extracted_files={},
            scenario_metadata_path=downloaded_bundle_meta,
        ),
    )
    mock_input_manager = mocker.patch("RUFAS.task_manager.InputManager", autospec=True)
    mock_im_instance = mock_input_manager.return_value
    mock_im_instance.start_data_processing.return_value = True

    tm = TaskManager()
    tm.start(
        metadata_path=tm_meta_path,
        remote_config_path=tmp_path / "bundle_cfg.json",
        suppress_log_files=True,
    )

    called_path = mock_im_instance.start_data_processing.call_args[0][0]
    assert Path(called_path) == downloaded_bundle_meta


def test_task_manager_original_scenario_metadata_unmodified(tmp_path: Path, mocker: MockerFixture) -> None:
    original_meta_content = json.dumps({
        "files": {
            "weather": {
                "path": "input/data/weather/default.csv",
                "type": "csv",
                "properties": "weather_properties",
                "remote_source": "config/remote_weather.json",
            }
        }
    })
    scenario_path = tmp_path / "scenario_metadata.json"
    scenario_path.write_text(original_meta_content, encoding="utf-8")

    args = {
        "task_id": "nondestructive_test",
        "metadata_file_path": str(scenario_path),
    }

    mocker.patch(
        "RUFAS.adapters.RemoteDataAdapter.prepare_data",
        return_value=RemoteFetchResult(extracted_files={"weather": tmp_path / "downloaded.csv"}),
    )

    TaskManager._resolve_task_remote_data(args)

    # Ephemeral file was created and assigned to args
    assert Path(args["metadata_file_path"]).name == ".runtime_nondestructive_test_metadata.json"
    # Original file on disk is completely untouched
    assert scenario_path.read_text(encoding="utf-8") == original_meta_content


def test_task_manager_no_remote_source(tmp_path: Path, mocker: MockerFixture) -> None:
    scenario_meta = {
        "files": {
            "weather": {
                "path": "input/data/weather/default.csv",
                "type": "csv",
                "properties": "weather_properties",
            }
        }
    }
    scenario_path = tmp_path / "scenario_metadata.json"
    scenario_path.write_text(json.dumps(scenario_meta), encoding="utf-8")

    args = {
        "task_id": "local_run",
        "metadata_file_path": str(scenario_path),
    }

    mock_adapter = mocker.patch("RUFAS.adapters.RemoteDataAdapter")

    TaskManager._resolve_task_remote_data(args)

    mock_adapter.assert_not_called()
    assert args["metadata_file_path"] == str(scenario_path)
