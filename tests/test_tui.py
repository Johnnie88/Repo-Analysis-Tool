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

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_analysis.tui import (
    ConfirmModal,
    MessageModal,
    InputModal,
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