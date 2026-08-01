# Contributing Guide

Thank you for contributing to the Repository Intelligence CLI Tool! This guide covers best practices for development, testing, and submitting changes.

## Development Setup

```bash
# Clone and setup
git clone https://github.com/Johnnie88/Repo-Analysis-Tool.git
cd Repo-Analysis-Tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install cloc (required for accurate LOC counts)
# Windows: choco install cloc
# macOS: brew install cloc
# Linux: sudo apt install cloc
```

## Code Style

### Linting & Formatting
```bash
# Check style
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/

# Format check
ruff format --check src/ tests/

# Auto-format
ruff format src/ tests/
```

### Type Checking
```bash
mypy src/
```

### Pre-commit Hooks (Recommended)
```bash
pip install pre-commit
pre-commit install
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/repo_analysis --cov-report=term-missing

# Run specific test file
pytest tests/test_analyzer.py -v

# Run tests matching pattern
pytest tests/ -k "test_countLoc" -v
```

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only |
| `develop` | Integration branch (if used) |
| `feature/*` | New features |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation only |
| `chore/*` | Maintenance (deps, CI, etc.) |

**Naming convention**: `feature/1-short-description`, `fix/2-bug-description`

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Formatting, no code change
- `refactor` - Code restructuring
- `test` - Adding/modifying tests
- `chore` - Maintenance, deps, CI
- `perf` - Performance improvement

### Examples
```
feat(tui): add cleanup flow for cloned repos
fix(analyzer): handle empty git history
docs(readme): update installation instructions
test(analyzer): add test for computeSimilarity
chore(deps): update textual to 0.53.0
```

## Pull Request Process

1. **Create feature branch** from `main`
2. **Make changes** with tests
3. **Run full test suite**: `pytest tests/ -v`
4. **Run linters**: `ruff check src/ tests/ && mypy src/`
5. **Update CHANGELOG.md** (if user-facing change)
6. **Update documentation** if needed
7. **Push branch** and create PR

### PR Requirements
- [ ] All tests pass
- [ ] Linting passes
- [ ] Type checking passes
- [ ] CHANGELOG.md updated (for feat/fix)
- [ ] Documentation updated (if applicable)
- [ ] License headers on new files
- [ ] No sensitive data in commits

## Code Guidelines

### Python
- **Type hints** required for public functions
- **Docstrings** for all public classes/functions (Google style)
- **Max line length**: 100 characters
- **Import order**: stdlib → third-party → local
- **No wildcard imports**

### File Headers
All source files must include MIT license header:
```python
# Repository Intelligence CLI Tool
# Copyright (c) 2024 Repository Intelligence Team
#
# Permission is hereby granted...
```

### Security
- **Never commit secrets** (tokens, keys, passwords)
- Sensitive env vars are auto-cleared at TUI startup
- Use `--github-token` CLI flag or TUI input for tokens
- No hardcoded credentials

### Testing
- **Test coverage** target: >80% for new code
- **Unit tests** for pure functions
- **Integration tests** for API calls (mocked)
- **Fixtures** in `conftest.py` for shared setup

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. After merge, tag release: `git tag v3.1.0 && git push --tags`
5. GitHub Actions builds and publishes to PyPI

## Getting Help

- Check existing issues
- Read `docs/AGENTS.md` for architecture overview
- Read `docs/csv_schema.md` for output format
- Open a discussion for design questions

## Code of Conduct

Be respectful, inclusive, and constructive. See [GitHub Community Guidelines](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines).