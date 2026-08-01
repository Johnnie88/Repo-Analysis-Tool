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

"""Tests for the tui_backend module."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_analysis.tui_backend import (
    sanitize_str,
    get_github_web_token_url,
    get_azure_web_token_url,
    check_company_exists_github,
    check_company_exists_azure,
    check_company,
)


class TestTUIBackend:
    """Test cases for TUI backend functions."""

    def test_sanitize_str(self):
        """Test string sanitization."""
        assert sanitize_str("hello") == "hello"
        assert sanitize_str("hello`world") == "helloworld"
        assert sanitize_str("hello$world") == "helloworld"
        assert sanitize_str("hello\\world") == "helloworld"
        assert sanitize_str('hello"world') == "hello'world"
        assert sanitize_str("hello\nworld") == "hello world"
        assert sanitize_str("hello\rworld") == "helloworld"  # \r is removed, not replaced
        assert sanitize_str("") == ""
        assert sanitize_str(None) == ""

    def test_get_github_web_token_url(self):
        """Test GitHub token URL generation."""
        url = get_github_web_token_url()
        assert "github.com/settings/tokens/new" in url
        assert "repo,read:org,read:user" in url
        assert "Repo_Analysis_Tool_TUI" in url

    def test_get_azure_web_token_url(self):
        """Test Azure DevOps token URL generation."""
        url = get_azure_web_token_url("myorg")
        assert "dev.azure.com/myorg/_usersSettings/tokens" in url

    @pytest.mark.asyncio
    async def test_check_company_exists_github_not_found(self):
        """Test GitHub company check - not found."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.__enter__.return_value = mock_response
            mock_response.read.return_value = b'{"message": "Not Found"}'
            mock_response.getcode.return_value = 404
            
            import urllib.error
            mock_response.__exit__.return_value = False
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://api.github.com/orgs/nonexistent", 404, "Not Found", {}, None
            )
            
            exists, msg = check_company_exists_github("nonexistent")
            assert not exists
            assert "does not exist" in msg

    @pytest.mark.asyncio
    async def test_check_company_exists_azure_not_found(self):
        """Test Azure DevOps company check - not found."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            import urllib.error
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://dev.azure.com/nonexistent/_apis/projects", 404, "Not Found", {}, None
            )
            
            exists, msg = check_company_exists_azure("nonexistent")
            assert not exists
            assert "does not exist" in msg

    def test_check_company_github(self):
        """Test unified check_company for GitHub."""
        with patch("repo_analysis.tui_backend.check_company_exists_github") as mock_check:
            mock_check.return_value = (True, "Organization found")
            exists, msg = check_company("github", "testorg")
            assert exists
            assert msg == "Organization found"

    def test_check_company_azure(self):
        """Test unified check_company for Azure."""
        with patch("repo_analysis.tui_backend.check_company_exists_azure") as mock_check:
            mock_check.return_value = (True, "Organization found")
            exists, msg = check_company("azure", "testorg")
            assert exists
            assert msg == "Organization found"