"""Additional coverage tests for run_service.py edge cases."""

import asyncio
import os
from unittest.mock import MagicMock, mock_open, patch

from src.run_service import (_save_and_update_titles,
                             _update_titles_in_todoist, main)


def test_update_titles_in_todoist_with_exception():
    """Test that exceptions during title updates are caught and logged."""
    to_update = [("task1", "New Title")]
    token = "fake_token"

    mock_api = MagicMock()
    mock_api.update_task.side_effect = Exception("API Error")

    with patch("src.run_service.TodoistAPI", return_value=mock_api):
        with patch("src.run_service.logger") as mock_logger:
            # Should not raise, but log the error
            asyncio.run(_update_titles_in_todoist(to_update, token))

            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Failed to update task" in str(mock_logger.error.call_args)


def test_save_and_update_titles_write_error_on_second_save():
    """Test OSError when writing the updated result file."""

    async def fake_run_todoist():
        return {"status": "ok"}

    result = {
        "status": "ok",
        "today_tasks": [{"id": "1", "title": {"to_replace": True, "combined": "new"}}],
    }
    out_file = "/tmp/test_output.json"

    write_attempts = []

    def track_open(
        filename, mode="r", encoding=None
    ):  # pylint: disable=unused-argument
        write_attempts.append(filename)
        if len(write_attempts) == 1:
            # First write succeeds
            return mock_open(read_data="")()
        # Second write fails
        raise OSError("Disk full")

    with patch("src.run_service.run_todoist_integration", new=fake_run_todoist):
        with patch("builtins.open", side_effect=track_open):
            with patch.dict(os.environ, {"TODOIST_SECRET_ID": "fake_token"}):
                with patch("src.run_service.TodoistAPI") as mock_api_cls:
                    mock_api = MagicMock()
                    mock_api_cls.return_value = mock_api

                    with patch("src.run_service.logger"):
                        with patch("builtins.print"):
                            # Should not raise, should print error
                            asyncio.run(_save_and_update_titles(result, out_file))

                            # Should have attempted two writes
                            assert len(write_attempts) == 2


def test_main_with_exception():
    """Test main function when run_todoist_integration raises exception."""

    async def fake_failing_integration():
        raise RuntimeError("Integration failed")

    with patch("src.run_service.run_todoist_integration", new=fake_failing_integration):
        with patch("builtins.print") as mock_print:
            exit_code = asyncio.run(main())

            # Should return 1
            assert exit_code == 1

            # Should print error
            error_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Error executing service" in str(call) for call in error_calls)


def test_save_and_update_titles_with_non_dict_parsed():
    """Test _save_and_update_titles when parsed result is not a dict."""

    # Result that will parse to None (not a dict)
    result = "invalid result"
    out_file = "/tmp/test_output.json"

    with patch("builtins.open", mock_open()):
        with patch("builtins.print"):
            returned = asyncio.run(_save_and_update_titles(result, out_file))

            # Should return original result when parsed is not dict
            assert returned == result
