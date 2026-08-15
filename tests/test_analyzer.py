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

"""Tests for the analyzer module."""

# Import the analyzer module
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repo_analysis.analyzer import (
    EXT_TO_LANG_MAP,
    SKIP_DIRS,
    SKIP_EXTENSIONS,
    classifyFile,
    computeLanguageBreakdown,
    computeSimilarity,
    countLexicalTokens,
    countLoc,
    hashFile,
    isBinary,
    processFileBatch,
    readFileSafe,
)


class TestAnalyzer:
    """Test cases for analyzer utility functions."""

    def test_countLoc(self):
        """Test line counting."""
        assert countLoc("") == 0
        assert countLoc("line1\n") == 1
        assert countLoc("line1\nline2\nline3") == 3
        assert countLoc("  \n  \n") == 0  # blank lines
        assert countLoc("# comment\ncode\n") == 2

    def test_countLexicalTokens(self):
        """Test lexical token counting."""
        tokens = countLexicalTokens("def hello(): return 42")
        assert "def" in tokens
        assert "hello" in tokens
        assert "return" in tokens
        assert "42" in tokens

    def test_computeSimilarity(self):
        """Test Jaccard similarity computation."""
        # Identical sets
        assert computeSimilarity(["a", "b", "c"], ["a", "b", "c"]) == 1.0
        # Disjoint sets
        assert computeSimilarity(["a", "b"], ["c", "d"]) == 0.0
        # Partial overlap
        assert computeSimilarity(["a", "b", "c"], ["b", "c", "d"]) == 0.5
        # Empty sets
        assert computeSimilarity([], []) == 1.0
        assert computeSimilarity([], ["a"]) == 0.0

    def test_classifyFile(self):
        """Test file classification."""
        # Python files
        assert classifyFile("test.py", ".py") == (True, "code")
        # Markdown files
        assert classifyFile("README.md", ".md") == (False, "non-code")
        # Excluded files
        assert classifyFile("README", "") == (False, "excluded")
        # Special code files
        assert classifyFile("Dockerfile", "") == (True, "code")
        assert classifyFile("Makefile", "") == (True, "code")

    def test_isBinary(self, tmp_path):
        """Test binary file detection."""
        # Create a text file
        text_file = tmp_path / "test.txt"
        text_file.write_text("hello world")
        assert not isBinary(str(text_file))

        # Create a binary file
        bin_file = tmp_path / "test.bin"
        bin_file.write_bytes(b"\x00\x01\x02\x03")
        assert isBinary(str(bin_file))

    def test_hashFile(self, tmp_path):
        """Test file hashing."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        hash1 = hashFile(str(test_file))
        hash2 = hashFile(str(test_file))
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex

    def test_readFileSafe(self, tmp_path):
        """Test safe file reading."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        content = readFileSafe(str(test_file))
        assert content == "hello world"

        # Non-existent file
        assert readFileSafe("/nonexistent/file.txt") is None

    def test_extension_maps(self):
        """Test extension to language mapping."""
        assert EXT_TO_LANG_MAP[".py"] == "Python"
        assert EXT_TO_LANG_MAP[".js"] == "JavaScript"
        assert EXT_TO_LANG_MAP[".ts"] == "TypeScript"
        assert EXT_TO_LANG_MAP[".go"] == "Go"
        assert EXT_TO_LANG_MAP[".rs"] == "Rust"

    def test_skip_dirs(self):
        """Test skip directories."""
        assert ".git" in SKIP_DIRS
        assert "node_modules" in SKIP_DIRS
        assert "__pycache__" in SKIP_DIRS
        assert "venv" in SKIP_DIRS

    def test_skip_extensions(self):
        """Test skip extensions."""
        assert ".pyc" in SKIP_EXTENSIONS
        assert ".exe" in SKIP_EXTENSIONS
        assert ".jpg" in SKIP_EXTENSIONS
        assert ".json" in SKIP_EXTENSIONS

    def test_processFileBatch_special_tokens(self, tmp_path):
        """Files containing special tokens must be tokenized, not silently dropped."""
        code_file = tmp_path / "tokens.py"
        code_file.write_text("x = 1 <|endoftext|> <|startoftext|>")
        results = processFileBatch([str(code_file)])
        assert len(results) == 1
        assert results[0]["llm_tokens"] > 0
        assert results[0]["filepath"] == str(code_file)

    def test_computeLanguageBreakdown(self):
        """Breakdown must compute percentages without raising NameError."""
        breakdown = computeLanguageBreakdown(["a.py", "b.js"], {"a.py": 75, "b.js": 25})
        assert breakdown["language_count"] == 2
        langs = {lang: info["pct"] for lang, info in breakdown["breakdown"].items()}
        assert langs["Python"] == 75.0
        assert langs["JavaScript"] == 25.0
        assert breakdown["breakdown"]["Python"]["files"] == 1
