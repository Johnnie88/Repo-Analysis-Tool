# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Cross-platform launchers** at the repo root — `run` (bash / Linux / macOS / WSL) and `run.bat` (Windows):
  - Auto-select the `venv/` interpreter with fallback to system `python`/`python3`
  - Prepend `src/` to `PYTHONPATH`, so it works without `pip install -e`
  - `run` (no args) starts the interactive analyzer; CLI args pass straight through
  - `run tui`, `run backend <args...>`, and `run help` subcommands

### Fixed
- **`analyzer.py`** — `computeLanguageBreakdown()` no longer raises `NameError` (`total_loc` → `totalLoc`); language percentage shares now compute correctly
- **`analyzer.py`** — files containing tiktoken special tokens (e.g. `<|endoftext|>`) are now tokenized and counted instead of being silently dropped by `processFileBatch()`
- **`analyzer.py`** — removed the dead, shadowed first definition of `runInteractiveMode()`; the active token-prompting version is now the single source of truth
- **`analyzer.py`** — Stage 2 / AI-detection duplication sanity checks log an error instead of raising `ValueError`, so legitimate repos no longer abort the whole run
- **`analyzer.py`** — simplified the redundant exception handler in `runGit()` and removed the dead `except subprocess.CalledProcessError` branch in `cloneRepo()`
- **`analyzer.py`** — `runCloc()` / `callGitLabApi()` now type their defaulted parameters as `Optional[...]` instead of implicit `None`
- **`tui.py`** — repository selection now actually works: the "Select" column gets a proper key, space/click toggling resolves the row via `coordinate_to_cell_key()` (the previous `get_row_at()[3]` returned the checkbox text, not a row key), and the "Select All" path yields string tags instead of `RowKey` objects (previously crashed in `" ".join()`)
- **`tui.py`** — simplified the dead `if self.from_web / else` branch in `PATInputScreen.action_go_back()`

### Tests
- Added regression tests for the special-token tokenization and language-breakdown fixes (`tests/test_analyzer.py`) and for the TUI space-key toggle and select-all behavior (`tests/test_tui.py`); suite now **26 tests** (was 22)

## [3.0.0] - 2026-08-01

### Added
- **Cross-platform TUI** using Textual framework (`src/repo_analysis/tui.py`)
  - Works on Windows, Linux, macOS without external dependencies
  - Modern UI with DataTable, RichLog, ProgressBar, Modal dialogs
  - Full flow: Platform → Target → Auth → Visibility → Fetch → Select → Analyze → Summary
- **Proper Python package structure** (`src/repo_analysis/`)
  - `analyzer.py` - Main analyzer (formerly `Repo_analysis_tool.py`)
  - `tui.py` - Textual TUI
  - `tui_backend.py` - GitHub/Azure DevOps API backend
  - `scripts/tui_textual.sh` - Cross-platform TUI launcher
  - `scripts/tui_analyzer.sh` - Legacy bash TUI launcher (dialog/whiptail)
- **Entry points** via `pyproject.toml`:
  - `repo-analysis` - Main CLI
  - `repo-analysis-tui` - Textual TUI
  - `repo-analysis-tui-backend` - Backend API commands
- **Test suite** (`tests/`) with 22 passing tests:
  - `test_analyzer.py` - Core analyzer utilities
  - `test_tui.py` - TUI modal components
  - `test_tui_backend.py` - Backend API functions
- **Documentation** moved to `docs/`:
  - `AGENTS.md` - Agent guidance
  - `README.md` - Project overview
  - `csv_schema.md` - CSV column reference
  - `CSV_CHEATSHEET.md` - Quick CSV reference
- **GitHub Actions CI workflow** (`.github/workflows/ci.yml`):
  - Linting with Ruff
  - Type checking with MyPy
  - Tests with pytest on Python 3.8-3.12
  - Cross-platform (Ubuntu, Windows, macOS)

### Changed
- Restructured from single-file layout to proper `src/` package layout
- Requirements updated: added `textual>=0.52.0` for cross-platform TUI
- Legacy bash TUI preserved in `scripts/tui_analyzer.sh` for Linux/macOS
- Updated `AGENTS.md` with new structure and commands
- Removed generated files from version control (`.tui_repo_map.json`, `batch_repos.txt`, `__pycache__`, `.pytest_cache`, `.egg-info`)

### Removed
- Root-level `Repo_analysis_tool.py` (moved to `src/repo_analysis/analyzer.py`)
- Root-level `tui_analyzer.sh` (moved to `scripts/tui_analyzer.sh`)
- Root-level `tui_backend.py` (moved to `src/repo_analysis/tui_backend.py`)
- Root-level markdown files (moved to `docs/`)
- `alien-build-git-data/` external repo data

### Fixed
- `sanitize_str()` now correctly handles carriage returns
- TUI space key handling for repository selection
- Path resolution in TUI for new package structure

## [2.0.0] - Previous version

### Added
- Multi-stage analysis pipeline (6 stages)
- GitHub PR analytics (Stage 0.5)
- AI-generated code detection (Stage 3)
- Security scanning for secrets (Stage 5)
- Professional CSV reporting (`summary_all.csv`, `summary_metadata.csv`)
- JSON per-repo reports
- Infrastructure detection (databases, deployment, APIs)
- Framework detection from manifests and imports
- Repository rating system (0-10 composite score)

## [1.0.0] - Initial release

### Added
- Basic Git metadata extraction
- Code metrics (LOC, tokens)
- Language detection via cloc
- Directory structure analysis
- Batch processing mode
- GitHub and Azure DevOps integration