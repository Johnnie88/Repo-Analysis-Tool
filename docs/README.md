# Repository Intelligence CLI Tool (v3.0.0)

A high-performance, multi-stage static analysis pipeline designed to transform raw codebases into actionable intelligence. This tool performs deep analysis on Git metadata, code metrics, architectural patterns, and security risks.

## 🛠️ Setup & Requirements

### 1. Python Environment

Ensure you have Python 3.8+ installed.

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

```bash
# Linux/macOS
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Install `cloc` (Critical for accuracy)

The tool uses `cloc` to calculate precise "Ground Truth" line counts and language breakdowns.

#### Windows Setup

* **Recommendation**: Install via Chocolatey:
  ```powershell
  choco install cloc
  ```
  Or place `cloc.exe` in the tool directory or your system's PATH.

#### macOS Setup

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install cloc
brew install cloc
```

#### Linux Setup

* **Debian/Ubuntu**: `sudo apt update && sudo apt install -y cloc`
* **RedHat/Fedora**: `sudo dnf install -y cloc`
* **Arch Linux**: `sudo pacman -S cloc`

#### Verify Installation

```bash
cloc --version
```

### 6. Git Installation

Ensure `git` is installed and available in your terminal so the tool can clone remote repositories and analyze commit history.

## 📖 Usage

### Cross-Platform TUI (Recommended)

Modern Textual-based TUI works on Windows, Linux, and macOS:

```bash
./scripts/tui_textual.sh
```

Or directly:

```bash
python -m repo_analysis.tui
```

### Legacy Bash TUI (Linux/macOS only)

Uses `dialog`/`whiptail`:

```bash
./scripts/tui_analyzer.sh
```

### CLI Commands

```bash
# Interactive menu
python -m repo_analysis.analyzer

# Analyze local directory
python -m repo_analysis.analyzer -i "/path/to/project" -o ./outputs --mode full

# Analyze remote repository (GitHub)
python -m repo_analysis.analyzer -i https://github.com/user/repo.git --mode full

# With GitHub PR analytics
python -m repo_analysis.analyzer -i https://github.com/user/repo.git --github-token YOUR_PAT

# Batch mode (one URL/path per line in repos.txt)
python -m repo_analysis.analyzer --batch repos.txt -o ./outputs
```

### Backend API Commands

```bash
# Generate GitHub PAT URL
python -m repo_analysis.tui_backend get-url --provider github --org myorg

# Fetch repositories
python -m repo_analysis.tui_backend fetch-repos --provider github --target myorg --visibility all

# Summarize high-rating repos
python -m repo_analysis.tui_backend summarize-rating --output-dir ./outputs --format text
```

## 🚀 Key Features

### 1. Multi-Stage Analysis Pipeline

The tool executes analysis in organized layers to ensure a separation between ground truth (verified tools) and heuristic estimates:

- **Stage 0 (Git Meta)**: Extracts commit counts, unique & total contributor diversity, active span, and history integrity.
- **Stage 0.5 (GitHub PR Analytics)**: Optionally extracts Pull Request metrics (total, open, closed, merged counts) and dumps full PR metadata to OS-safe JSON files if `GITHUB_TOKEN` or `GH_TOKEN` env is available.
- **Stage 1 (Structure)**: Scans directory hierarchy for architectural signals and framework manifests.
- **Stage 2 (Deep Metrics)**: Calculates verified LOC (via `cloc`), LLM token density (via `tiktoken`), and cross-file duplication.
- **Stage 3 (AI Detection)**: Uses entropy and token distribution heuristics to identify AI-generated code.
- **Stage 4 (Intelligence)**: Categorizes Frontend vs. Backend logic, detects infrastructure (Databases, Cloud, APIs) at all depths, and evaluates documentation quality.
- **Stage 5 (Security)**: Scans for exposed credentials, AWS keys, and database connection strings.

### 2. Advanced Infrastructure Detection (v3.0.0)

- **Canonical Reporting**: Automatically groups database aliases (e.g., `postgres` and `postgresql` → `PostgreSQL`).
- **Greedy Scanning**: Peeks inside source code files (`.py`, `.js`, `.go`, etc.) to identify library imports and connection strings.
- **Full-Depth Scanning**: Recursively analyzes the entire repository without depth limits.

### 3. Professional CSV Reporting

Generates standardized CSV outputs for at-scale repository auditing:

- **`summary_all.csv`**: A comprehensive dataset featuring 40+ parameters including contributor mapping, complexity, architectural splits, and security findings.
- **`summary_metadata.csv`**: A curated executive summary focused on commercial usage, security status, and core architectural labels.

*For a detailed breakdown of what each CSV column means, please refer to the [`csv_schema.md`](./csv_schema.md) document.*

### 4. Robust Input Handling

- **Quote-Resistant Paths**: Automatically strips double-quotes from paths pasted from Windows File Explorer ("Copy as path").
- **Batch Processing**: Supports a single `.txt` file containing a mix of local directory paths and remote Git URLs.

### 5. Cross-Platform TUI (v3.0.0)

Modern terminal UI using Textual framework:
- Works on **Windows, Linux, macOS** without external dependencies
- DataTable-based repository selection with keyboard shortcuts
- Live log output during batch analysis
- Modal dialogs for input/confirmation
- Progress bars for long-running operations

### 6. Automatic Cleanup

- **At startup**: Clears sensitive tokens from environment (`GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `AZURE_TOKEN`, etc.)
- **After analysis**: Removes cloned repositories (`cloned_repos/`) and temporary files (`batch_repos.txt`, `.tui_repo_map.json`)
- **On quit**: Same cleanup runs on Ctrl+C

## 📊 Outputs

The tool generates professional-grade reports in the `./outputs` folder:

1. **`summary_all.csv`**: Master dataset for data processing and audit reporting.
2. **`summary_metadata.csv`**: Curated metadata report for executive review.
3. **`{repo}_report.json`**: Deep-dive technical breakdown for each analyzed repository.

## 📁 Project Structure

```
Repo-Analysis-Tool/
├── src/
│   └── repo_analysis/
│       ├── __init__.py
│       ├── analyzer.py       # Main analyzer (CLI + library)
│       ├── tui.py            # Cross-platform TUI (Textual)
│       └── tui_backend.py    # API backend (GitHub/Azure DevOps)
├── tests/                    # Test suite (22 tests)
├── scripts/
│   ├── tui_textual.sh        # Cross-platform TUI launcher
│   └── tui_analyzer.sh       # Legacy bash TUI launcher
├── docs/
│   ├── AGENTS.md             # Agent guidance
│   ├── README.md             # This file
│   ├── csv_schema.md         # CSV column reference
│   └── CSV_CHEATSHEET.md     # Quick CSV reference
├── .github/workflows/ci.yml  # GitHub Actions CI
├── pyproject.toml            # Package config
├── requirements.txt
└── CHANGELOG.md
```

## 🧪 Development

### Run Tests

```bash
pytest tests/ -v
```

### Install in Development Mode

```bash
pip install -e ".[dev]"
```

### Linting & Type Checking

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
```

## 📝 License

MIT License — Developed for Advanced Repository Intelligence & Technical Auditing.