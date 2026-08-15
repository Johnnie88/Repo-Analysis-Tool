# Repository Intelligence CLI Tool
# Copyright (c) 2024 Repository Intelligence Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Tests for the TUI module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_analysis.tui import (
    ConfirmModal,
    InputModal,
    MessageModal,
    ProgressModal,
)


class TestTUIModals:
    """Test cases for TUI modal dialogs."""

    def test_confirm_modal_creation(self):
        """Test ConfirmModal creation."""
        modal = ConfirmModal("Are you sure?", "Confirm")
        assert modal.message == "Are you sure?"
        assert modal.title == "Confirm"

    def test_message_modal_creation(self):
        """Test MessageModal creation."""
        modal = MessageModal("Hello world", "Info")
        assert modal.message == "Hello world"
        assert modal.title == "Info"

    def test_input_modal_creation(self):
        """Test InputModal creation."""
        modal = InputModal("Enter name:", "Input", default="test")
        assert modal.prompt == "Enter name:"
        assert modal.title == "Input"
        assert modal.default == "test"
        assert modal.password is False

    def test_input_modal_password(self):
        """Test InputModal with password."""
        modal = InputModal("Enter password:", "Input", password=True)
        assert modal.password is True

    def test_progress_modal_creation(self):
        """Test ProgressModal creation."""
        modal = ProgressModal("Working...", "Please wait")
        assert modal.title == "Working..."
        assert modal.message == "Please wait"


class TestRepoSelectionScreen:
    """Test cases for the repository selection screen."""

    REPOS = [
        {"name": "repo-a", "desc": "first", "url": "u1"},
        {"name": "repo-b", "desc": "second", "url": "u2"},
    ]

    def _screen(self):
        from repo_analysis.tui import RepoSelectionScreen

        return RepoSelectionScreen(list(self.REPOS))

    def test_space_toggles_cursor_row(self):
        """Space must toggle the row under the cursor (not the checkbox cell text)."""
        import asyncio

        from textual.widgets import DataTable

        async def scenario():
            from textual.app import App

            async with App().run_test() as pilot:
                await pilot.app.push_screen(self._screen())
                await pilot.pause()
                table = pilot.app.screen.query_one("#repo-table", DataTable)
                await pilot.press("space")
                assert table.get_row("R1")[3] == "[X]"
                await pilot.press("space")
                assert table.get_row("R1")[3] == "[ ]"

        asyncio.run(scenario())

    def test_select_all_updates_all_rows(self):
        """Select-all must toggle every row including the SELECT ALL row."""
        import asyncio

        from textual.widgets import DataTable

        async def scenario():
            from textual.app import App

            async with App().run_test() as pilot:
                await pilot.app.push_screen(self._screen())
                await pilot.pause()
                table = pilot.app.screen.query_one("#repo-table", DataTable)
                await pilot.press("a")
                assert table.get_row("R0")[3] == "[X]"
                assert table.get_row("R1")[3] == "[X]"

        asyncio.run(scenario())
