#!/usr/bin/env python3
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
"""
Repository Intelligence CLI Tool - Cross-platform TUI (Textual)
Replaces tui_analyzer.sh with a pure Python implementation using Textual.
Works on Windows, Linux, and macOS.
"""

import asyncio
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button, Checkbox, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, Markdown, ProgressBar, RadioButton, RadioSet,
    RichLog, Select, Static, TabbedContent, TabPane, TextArea
)
from textual.screen import Screen, ModalScreen
from textual.message import Message
from textual.reactive import reactive
from textual.events import Key
from rich.text import Text

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Go up to v1.0 root
BATCH_FILE = PROJECT_ROOT / "batch_repos.txt"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
REPO_MAP_FILE = PROJECT_ROOT / ".tui_repo_map.json"
CLONE_DIR = PROJECT_ROOT / "cloned_repos"

PYTHON_BIN = PROJECT_ROOT / "venv" / "bin" / "python"
if not PYTHON_BIN.exists():
    PYTHON_BIN = Path(sys.executable)

TUI_BACKEND = PROJECT_ROOT / "src" / "repo_analysis" / "tui_backend.py"
ANALYZER = PROJECT_ROOT / "src" / "repo_analysis" / "analyzer.py"

# Sensitive environment variables to clear at startup
SENSITIVE_ENV_VARS = [
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITLAB_TOKEN",
    "AZURE_TOKEN",
    "GITHUB_PAT",
    "GITLAB_PAT",
    "AZURE_PAT",
]

def clear_sensitive_env() -> None:
    """Clear sensitive environment variables at startup to prevent leaks."""
    for var in SENSITIVE_ENV_VARS:
        if var in os.environ:
            del os.environ[var]

def cleanup_cloned_repos() -> None:
    """Remove all cloned repositories after analysis."""
    if CLONE_DIR.exists():
        import shutil
        try:
            shutil.rmtree(CLONE_DIR)
        except Exception:
            pass

def cleanup_batch_files() -> None:
    """Remove temporary batch files."""
    for f in [BATCH_FILE, REPO_MAP_FILE]:
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass


class ConfirmModal(ModalScreen[bool]):
    """Modal dialog for yes/no confirmation."""

    def __init__(self, message: str, title: str = "Confirm"):
        super().__init__()
        self.message = message
        self.title = title

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self.title, id="confirm-title")
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", variant="primary", id="yes-btn")
                yield Button("No", variant="default", id="no-btn")

    @on(Button.Pressed, "#yes-btn")
    def on_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no-btn")
    def on_no(self) -> None:
        self.dismiss(False)


class MessageModal(ModalScreen[None]):
    """Modal dialog for showing a message."""

    def __init__(self, message: str, title: str = "Message"):
        super().__init__()
        self.message = message
        self.title = title

    def compose(self) -> ComposeResult:
        with Container(id="message-dialog"):
            yield Label(self.title, id="message-title")
            yield Label(self.message, id="message-text")
            yield Button("OK", variant="primary", id="ok-btn")

    @on(Button.Pressed, "#ok-btn")
    def on_ok(self) -> None:
        self.dismiss(None)


class InputModal(ModalScreen[Optional[str]]):
    """Modal dialog for text input."""

    def __init__(self, prompt: str, title: str = "Input", default: str = "", password: bool = False):
        super().__init__()
        self.prompt = prompt
        self.title = title
        self.default = default
        self.password = password

    def compose(self) -> ComposeResult:
        with Container(id="input-dialog"):
            yield Label(self.title, id="input-title")
            yield Label(self.prompt, id="input-prompt")
            yield Input(
                value=self.default,
                password=self.password,
                id="input-field",
                placeholder="Enter value..."
            )
            with Horizontal(id="input-buttons"):
                yield Button("OK", variant="primary", id="ok-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#input-field", Input).focus()

    @on(Button.Pressed, "#ok-btn")
    def on_ok(self) -> None:
        value = self.query_one("#input-field", Input).value
        self.dismiss(value if value else None)

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        self.dismiss(None)

    @on(Input.Submitted, "#input-field")
    def on_submit(self) -> None:
        self.on_ok()


class ProgressModal(ModalScreen[None]):
    """Modal dialog showing progress of a long-running operation."""

    def __init__(self, title: str = "Working...", message: str = ""):
        super().__init__()
        self.title = title
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label(self.title, id="progress-title")
            yield Label(self.message, id="progress-message")
            yield ProgressBar(id="progress-bar", show_eta=False)
            yield RichLog(id="progress-log", markup=True, highlight=True)

    def update_progress(self, message: str, progress: float = None) -> None:
        log = self.query_one("#progress-log", RichLog)
        log.write(message)
        if progress is not None:
            bar = self.query_one("#progress-bar", ProgressBar)
            bar.update(progress=progress * 100)

    def set_message(self, message: str) -> None:
        self.query_one("#progress-message", Label).update(message)


class MainMenuScreen(Screen):
    """Main menu screen."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-menu"):
            yield Static("🔍 Repository Intelligence CLI Tool", id="title")
            yield Static("v3.0.0 — Multi-platform TUI", id="subtitle")
            yield Label("")
            yield Button("🐙 GitHub (User / Organization)", id="btn-github", variant="primary")
            yield Button("☁️  Azure DevOps (Organization / Project)", id="btn-azure", variant="primary")
            yield Button("📊 Summarize High-Rating Repositories", id="btn-summary", variant="default")
            yield Button("❌ Exit", id="btn-exit", variant="error")
        yield Footer()

    @on(Button.Pressed, "#btn-github")
    def on_github(self) -> None:
        self.app.push_screen(TargetInputScreen("github"))

    @on(Button.Pressed, "#btn-azure")
    def on_azure(self) -> None:
        self.app.push_screen(TargetInputScreen("azure"))

    @on(Button.Pressed, "#btn-summary")
    def on_summary(self) -> None:
        self.app.push_screen(SummaryScreen())

    @on(Button.Pressed, "#btn-exit")
    def on_exit(self) -> None:
        self.app.exit()


class TargetInputScreen(Screen):
    """Screen for entering target username/organization."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, provider: str):
        super().__init__()
        self.provider = provider

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="target-input"):
            yield Static(f"🎯 {self.provider.capitalize()} Target Selection", id="screen-title")
            yield Label("")
            if self.provider == "github":
                yield Label("Enter GitHub Username or Organization Name:")
                yield Label("(e.g., torvalds, google, facebook, or your username)", id="hint")
            else:
                yield Label("Enter Azure DevOps Organization Name:")
                yield Label("(e.g., my-company-org)", id="hint")
            yield Input(
                placeholder="Enter name...",
                id="target-input",
                value=""
            )
            with Horizontal(id="nav-buttons"):
                yield Button("← Back", id="btn-back", variant="default")
                yield Button("Continue →", id="btn-continue", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#target-input", Input).focus()

    @on(Button.Pressed, "#btn-back")
    @on(Button.Pressed, "#btn-cancel")
    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-continue")
    @on(Input.Submitted, "#target-input")
    def on_continue(self) -> None:
        target = self.query_one("#target-input", Input).value.strip()
        if not target:
            self.app.push_screen(MessageModal("Target name cannot be empty.", "Error"))
            return
        self.app.push_screen(AuthScreen(self.provider, target))


class AuthScreen(Screen):
    """Authentication method selection screen."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, provider: str, target: str):
        super().__init__()
        self.provider = provider
        self.target = target

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="auth-screen"):
            yield Static(f"🔐 {self.provider.capitalize()} Authentication", id="screen-title")
            yield Label("")
            yield Label(f"Target: {self.target}", id="target-label")
            yield Label("")
            yield RadioSet(
                RadioButton("🌐 Web Login (Open browser to generate PAT)", id="auth-web", value=True),
                RadioButton("🔑 Enter Existing Personal Access Token (PAT)", id="auth-pat"),
                RadioButton("👤 Anonymous / Public Repos Only (No Token)", id="auth-anon"),
                id="auth-options"
            )
            with Horizontal(id="nav-buttons"):
                yield Button("← Back", id="btn-back", variant="default")
                yield Button("Continue →", id="btn-continue", variant="primary")
        yield Footer()

    @on(Button.Pressed, "#btn-back")
    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-continue")
    def on_continue(self) -> None:
        radio_set = self.query_one("#auth-options", RadioSet)
        selected = radio_set.pressed_index
        if selected == 0:  # Web login
            self.app.push_screen(WebLoginScreen(self.provider, self.target))
        elif selected == 1:  # PAT entry
            self.app.push_screen(PATInputScreen(self.provider, self.target))
        else:  # Anonymous
            self.app.token = None
            self.app.push_screen(VisibilityScreen(self.provider, self.target, None))


class WebLoginScreen(Screen):
    """Screen showing web login URL and waiting for token."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, provider: str, target: str):
        super().__init__()
        self.provider = provider
        self.target = target

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="web-login"):
            yield Static(f"🌐 Web Login - {self.provider.capitalize()}", id="screen-title")
            yield Label("")
            yield Label("Opening browser to generate token...", id="status-label")
            yield Label("", id="url-label")
            yield Label("")
            yield Label("After generating token in browser, click Continue and paste it.", id="hint")
            with Horizontal(id="nav-buttons"):
                yield Button("← Back", id="btn-back", variant="default")
                yield Button("Continue →", id="btn-continue", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.generate_url())

    @work(exclusive=True)
    async def generate_url(self) -> None:
        try:
            result = subprocess.run(
                [str(PYTHON_BIN), str(TUI_BACKEND), "get-url",
                 "--provider", self.provider, "--org", self.target],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                self.url = url
                self.query_one("#url-label", Label).update(f"URL: {url}")
                self.query_one("#status-label", Label).update("✅ Browser opened. Generate token and return here.")
                webbrowser.open(url)
            else:
                self.query_one("#status-label", Label).update(f"❌ Error: {result.stderr}")
        except Exception as e:
            self.query_one("#status-label", Label).update(f"❌ Error: {e}")

    @on(Button.Pressed, "#btn-back")
    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-continue")
    def on_continue(self) -> None:
        self.app.push_screen(PATInputScreen(self.provider, self.target, from_web=True))


class PATInputScreen(Screen):
    """Screen for entering Personal Access Token."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, provider: str, target: str, from_web: bool = False):
        super().__init__()
        self.provider = provider
        self.target = target
        self.from_web = from_web

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="pat-input"):
            yield Static(f"🔑 Enter PAT - {self.provider.capitalize()}", id="screen-title")
            yield Label("")
            if self.from_web:
                yield Label("Paste the token you generated in the browser:", id="prompt")
            else:
                yield Label("Enter your Personal Access Token:", id="prompt")
            yield Input(
                placeholder="Paste token here...",
                password=True,
                id="pat-input"
            )
            yield Label("")
            yield Label("Token will be masked and stored only for this session.", id="hint")
            with Horizontal(id="nav-buttons"):
                yield Button("← Back", id="btn-back", variant="default")
                yield Button("Continue →", id="btn-continue", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#pat-input", Input).focus()

    @on(Button.Pressed, "#btn-back")
    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-continue")
    @on(Input.Submitted, "#pat-input")
    def on_continue(self) -> None:
        token = self.query_one("#pat-input", Input).value.strip()
        if not token:
            self.app.push_screen(MessageModal("Token cannot be empty.", "Error"))
            return
        self.app.token = token
        self.app.push_screen(VisibilityScreen(self.provider, self.target, token))


class VisibilityScreen(Screen):
    """Repository visibility selection screen."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, provider: str, target: str, token: Optional[str]):
        super().__init__()
        self.provider = provider
        self.target = target
        self.token = token

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="visibility-screen"):
            yield Static(f"👁️ Repository Visibility - {self.provider.capitalize()}", id="screen-title")
            yield Label("")
            yield Label(f"Target: {self.target}", id="target-label")
            yield Label(f"Auth: {'✅ Token provided' if self.token else '❌ Anonymous'}", id="auth-label")
            yield Label("")
            yield RadioSet(
                RadioButton("📂 All Repositories (Public + Private)", id="vis-all", value=True),
                RadioButton("🌍 Public Repositories Only", id="vis-public"),
                RadioButton("🔒 Private Repositories Only", id="vis-private"),
                id="vis-options"
            )
            yield Label("", id="warning-label")
            with Horizontal(id="nav-buttons"):
                yield Button("← Back", id="btn-back", variant="default")
                yield Button("Fetch Repositories →", id="btn-fetch", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.update_warning()

    @on(RadioSet.Changed, "#vis-options")
    def update_warning(self) -> None:
        radio_set = self.query_one("#vis-options", RadioSet)
        vis_map = {0: "all", 1: "public", 2: "private"}
        visibility = vis_map.get(radio_set.pressed_index, "all")

        warning = ""
        if not self.token and visibility == "private":
            warning = "⚠️ Private repositories require authentication. Falling back to Public only."
        elif self.provider == "github" and visibility == "private" and self.token:
            if self.target.lower() not in ("me", "self", "@me"):
                warning = ("ℹ️ Note: For GitHub, private repos are only accessible for:\n"
                           "  - Your own account (use 'me' as target)\n"
                           "  - Organizations you have admin access to (with token)")
        self.query_one("#warning-label", Label).update(warning)

    @on(Button.Pressed, "#btn-back")
    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-fetch")
    def on_fetch(self) -> None:
        radio_set = self.query_one("#vis-options", RadioSet)
        vis_map = {0: "all", 1: "public", 2: "private"}
        visibility = vis_map.get(radio_set.pressed_index, "all")

        if not self.token and visibility == "private":
            visibility = "public"

        self.app.visibility = visibility
        self.app.push_screen(ValidationScreen(self.provider, self.target, self.token, visibility))


class ValidationScreen(Screen):
    """Screen showing company/org validation progress."""

    def __init__(self, provider: str, target: str, token: Optional[str], visibility: str):
        super().__init__()
        self.provider = provider
        self.target = target
        self.token = token
        self.visibility = visibility

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="validation-screen"):
            yield Static(f"✅ Validating {self.provider.capitalize()} Organization", id="screen-title")
            yield Label("")
            yield Label(f"Target: {self.target}", id="target-label")
            yield Label(f"Visibility: {self.visibility}", id="vis-label")
            yield Label("")
            yield RichLog(id="validation-log", markup=True, highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.validate())

    @work(exclusive=True)
    async def validate(self) -> None:
        log = self.query_one("#validation-log", RichLog)
        log.write(f"[bold]Validating {self.provider.capitalize()} target: {self.target}[/bold]")

        cmd = [str(PYTHON_BIN), str(TUI_BACKEND), "check-company",
               "--provider", self.provider, "--target", self.target]
        if self.token:
            cmd.extend(["--token", self.token])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode() + stderr.decode()

            if output.startswith("EXISTS:"):
                log.write(f"[green]✅ {output[7:]}[/green]")
                await asyncio.sleep(0.5)
                self.app.push_screen(RepoFetchScreen(self.provider, self.target, self.token, self.visibility))
            elif output.startswith("NOT_FOUND:"):
                log.write(f"[red]❌ {output[10:]}[/red]")
                await asyncio.sleep(1)
                self.app.push_screen(MessageModal(output[10:], "Validation Failed"), callback=self.on_modal_dismiss)
            else:
                log.write(f"[yellow]⚠️ Unexpected response: {output}[/yellow]")
                await asyncio.sleep(1)
                self.app.push_screen(RepoFetchScreen(self.provider, self.target, self.token, self.visibility))
        except Exception as e:
            log.write(f"[red]❌ Validation error: {e}[/red]")
            await asyncio.sleep(1)
            self.app.push_screen(RepoFetchScreen(self.provider, self.target, self.token, self.visibility))

    def on_modal_dismiss(self, result: None) -> None:
        self.app.pop_screen()


class RepoFetchScreen(Screen):
    """Screen showing repository fetching progress."""

    def __init__(self, provider: str, target: str, token: Optional[str], visibility: str):
        super().__init__()
        self.provider = provider
        self.target = target
        self.token = token
        self.visibility = visibility
        self.repos: List[Dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="fetch-screen"):
            yield Static(f"📦 Fetching Repositories - {self.provider.capitalize()}", id="screen-title")
            yield Label("")
            yield Label(f"Target: {self.target}", id="target-label")
            yield Label(f"Visibility: {self.visibility}", id="vis-label")
            yield Label("")
            yield ProgressBar(id="fetch-progress", show_eta=False)
            yield RichLog(id="fetch-log", markup=True, highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.fetch_repos())

    @work(exclusive=True)
    async def fetch_repos(self) -> None:
        log = self.query_one("#fetch-log", RichLog)
        progress = self.query_one("#fetch-progress", ProgressBar)

        log.write(f"[bold]Fetching repositories for {self.target}...[/bold]")

        cmd = [str(PYTHON_BIN), str(TUI_BACKEND), "fetch-repos",
               "--provider", self.provider, "--target", self.target,
               "--visibility", self.visibility, "--format", "json"]
        if self.token:
            cmd.extend(["--token", self.token])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                log.write(f"[red]❌ Fetch failed: {stderr.decode()}[/red]")
                await asyncio.sleep(2)
                self.app.pop_screen()
                return

            data = json.loads(stdout.decode())
            self.repos = data

            # Save repo map for selection
            mapping = {"R0": {"name": "SELECT ALL", "url": "ALL", "desc": "ALL"}}
            mapping.update({f"R{idx}": r for idx, r in enumerate(self.repos, 1)})
            REPO_MAP_FILE.write_text(json.dumps(mapping, indent=2))

            log.write(f"[green]✅ Fetched {len(self.repos)} repositories[/green]")
            progress.update(progress=100)
            await asyncio.sleep(0.5)

            if not self.repos:
                self.app.push_screen(MessageModal(
                    f"No repositories found for '{self.target}'.\n\nPlease check the target name or token permissions.",
                    "No Repositories Found"
                ), callback=self.on_modal_dismiss)
            else:
                self.app.push_screen(RepoSelectionScreen(self.repos))

        except Exception as e:
            log.write(f"[red]❌ Fetch error: {e}[/red]")
            await asyncio.sleep(2)
            self.app.pop_screen()

    def on_modal_dismiss(self, result: None) -> None:
        self.app.pop_screen()


class RepoSelectionScreen(Screen):
    """Screen for selecting repositories to analyze."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("a", "select_all", "Select All"),
        Binding("n", "select_none", "Select None"),
    ]

    def __init__(self, repos: List[Dict]):
        super().__init__()
        self.repos = repos

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="selection-screen"):
            yield Static(f"☑️ Select Repositories to Analyze ({len(self.repos)} found)", id="screen-title")
            yield Label("")
            with Horizontal(id="selection-actions"):
                yield Button("☑️ Select All", id="btn-select-all", variant="default")
                yield Button("☐ Select None", id="btn-select-none", variant="default")
            yield Label("")
            yield DataTable(id="repo-table", cursor_type="row", zebra_stripes=True)
            yield Label("")
            yield Label("Press SPACE to toggle, A=Select All, N=Select None", id="hint")
            with Horizontal(id="nav-buttons"):
                yield Button("← Back", id="btn-back", variant="default")
                yield Button("Analyze Selected →", id="btn-analyze", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#repo-table", DataTable)
        table.add_columns("#", "Repository", "Description", ("Select", "Select"))
        for idx, repo in enumerate(self.repos, 1):
            table.add_row(
                str(idx),
                repo["name"],
                repo["desc"][:80] + ("..." if len(repo["desc"]) > 80 else ""),
                "☐",
                key=f"R{idx}"
            )
        table.add_row("0", "=== SELECT ALL ===", "All repositories", "☐", key="R0")
        table.focus()

    @on(DataTable.CellSelected, "#repo-table")
    def on_cell_selected(self, event: DataTable.CellSelected) -> None:
        if event.cell_key.column_key == "Select":
            self.toggle_selection(event.cell_key.row_key)

    def key_space(self, event: Key) -> None:
        table = self.query_one("#repo-table", DataTable)
        if table.cursor_row is not None:
            cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
            self.toggle_selection(cell_key.row_key)
            event.prevent_default().stop()

    def toggle_selection(self, row_key) -> None:
        table = self.query_one("#repo-table", DataTable)
        try:
            row = table.get_row(row_key)
            current = row[3]
            new = "☑️" if current == "☐" else "☐"
            table.update_cell(row_key, "Select", new)
        except Exception:
            pass

    def action_select_all(self) -> None:
        table = self.query_one("#repo-table", DataTable)
        for row_key in table.rows.keys():
            table.update_cell(row_key, "Select", "☑️")

    def action_select_none(self) -> None:
        table = self.query_one("#repo-table", DataTable)
        for row_key in table.rows.keys():
            table.update_cell(row_key, "Select", "☐")

    @on(Button.Pressed, "#btn-select-all")
    def on_select_all(self) -> None:
        self.action_select_all()

    @on(Button.Pressed, "#btn-select-none")
    def on_select_none(self) -> None:
        self.action_select_none()

    @on(Button.Pressed, "#btn-back")
    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-analyze")
    def on_analyze(self) -> None:
        table = self.query_one("#repo-table", DataTable)
        selected = []
        for row_key in table.rows.keys():
            row = table.get_row(row_key)
            if row[3] == "☑️" and row_key.value != "R0":
                selected.append(row_key.value)

        if not selected:
            # Check if "SELECT ALL" is selected
            try:
                all_row = table.get_row("R0")
                if all_row[3] == "☑️":
                    selected = [k.value for k in table.rows.keys() if k.value != "R0"]
            except Exception:
                pass

        if not selected:
            self.app.push_screen(MessageModal("No repositories selected for analysis.", "Error"))
            return

        self.app.selected_tags = " ".join(selected)
        self.app.push_screen(BatchAnalysisScreen(self.app.provider, self.app.target, self.app.token, self.app.visibility, selected))


class BatchAnalysisScreen(Screen):
    """Screen showing batch analysis progress."""

    def __init__(self, provider: str, target: str, token: Optional[str], visibility: str, selected_tags: List[str]):
        super().__init__()
        self.provider = provider
        self.target = target
        self.token = token
        self.visibility = visibility
        self.selected_tags = selected_tags
        self.process: Optional[asyncio.subprocess.Process] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="batch-screen"):
            yield Static("🚀 Batch Analysis Running", id="screen-title")
            yield Label("")
            yield Label(f"Provider: {self.provider.capitalize()}", id="provider-label")
            yield Label(f"Target: {self.target}", id="target-label")
            yield Label(f"Repositories: {len(self.selected_tags)}", id="count-label")
            yield Label("")
            yield ProgressBar(id="batch-progress", show_eta=False)
            yield RichLog(id="batch-log", markup=True, highlight=True, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.run_analysis())

    @work(exclusive=True)
    async def run_analysis(self) -> None:
        log = self.query_one("#batch-log", RichLog)
        progress = self.query_one("#batch-progress", ProgressBar)

        # Resolve selected tags to batch file
        cmd = [str(PYTHON_BIN), str(TUI_BACKEND), "resolve-selected",
               "--tags", " ".join(self.selected_tags), "--out", str(BATCH_FILE)]

        log.write("[bold]Resolving selected repositories...[/bold]")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            log.write(f"[red]❌ Resolve failed: {stderr.decode()}[/red]")
            return

        output = stdout.decode().strip()
        if output.startswith("SAVED:"):
            count = int(output.split(":")[1])
            log.write(f"[green]✅ {count} repositories saved to batch file[/green]")

        # Run batch analysis
        log.write("[bold]Starting batch analysis...[/bold]")
        cmd = [str(PYTHON_BIN), str(ANALYZER),
               "--batch", str(BATCH_FILE), "-o", str(OUTPUT_DIR)]
        if self.token:
            if self.provider == "github":
                cmd.extend(["--github-token", self.token])
            elif self.provider == "azure":
                cmd.extend(["--azure-token", self.token])

        log.write(f"[dim]Command: {' '.join(cmd)}[/dim]")

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Read output line by line
            line_count = 0
            async for line in self.process.stdout:
                line_count += 1
                decoded = line.decode(errors="replace").rstrip()
                if decoded:
                    log.write(decoded)

            await self.process.wait()

            if self.process.returncode == 0:
                log.write("[green]✅ Batch analysis completed successfully![/green]")
                progress.update(progress=100)
                await asyncio.sleep(1)
                
                # Cleanup: remove cloned repos and temporary files
                log.write("[bold]Cleaning up temporary files...[/bold]")
                cleanup_cloned_repos()
                cleanup_batch_files()
                log.write("[green]✅ Cleanup complete[/green]")
                
                self.app.push_screen(SummaryScreen(auto_show=True))
            else:
                log.write(f"[red]❌ Batch analysis failed with exit code {self.process.returncode}[/red]")

        except Exception as e:
            log.write(f"[red]❌ Error running analysis: {e}[/red]")

    def on_unmount(self) -> None:
        if self.process and self.process.returncode is None:
            self.process.terminate()


class SummaryScreen(Screen):
    """Screen showing high-rating repository summary."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, auto_show: bool = False):
        super().__init__()
        self.auto_show = auto_show

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="summary-screen"):
            yield Static("📊 High-Rating Repositories Summary", id="screen-title")
            yield Label("")
            yield RichLog(id="summary-log", markup=True, highlight=True, wrap=True)
            yield Label("")
            with Horizontal(id="nav-buttons"):
                yield Button("← Back to Menu", id="btn-back", variant="default")
                yield Button("🔄 Refresh", id="btn-refresh", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.load_summary())

    @work(exclusive=True)
    async def load_summary(self) -> None:
        log = self.query_one("#summary-log", RichLog)

        cmd = [str(PYTHON_BIN), str(TUI_BACKEND), "summarize-rating",
               "--output-dir", str(OUTPUT_DIR), "--format", "text"]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode()
                log.write(output)
            else:
                log.write(f"[red]Error loading summary: {stderr.decode()}[/red]")
        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")

    @on(Button.Pressed, "#btn-back")
    def action_go_back(self) -> None:
        # Pop all the way back to main menu
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()

    @on(Button.Pressed, "#btn-refresh")
    def action_refresh(self) -> None:
        self.run_worker(self.load_summary())


class RepoAnalysisApp(App):
    """Main TUI Application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-menu, #target-input, #auth-screen, #web-login, #pat-input,
    #visibility-screen, #validation-screen, #fetch-screen,
    #selection-screen, #batch-screen, #summary-screen {
        width: 100%;
        height: 100%;
        padding: 1 2;
        layout: vertical;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 0;
    }

    #subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    #screen-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #hint {
        color: $text-muted;
        text-style: italic;
    }

    #nav-buttons, #selection-actions {
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    #nav-buttons Button, #selection-actions Button {
        margin-right: 1;
    }

    #confirm-dialog, #message-dialog, #input-dialog, #progress-dialog {
        width: 80%;
        max-width: 80;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
        align: center middle;
    }

    #progress-dialog {
        width: 90%;
        max-width: 100;
        height: 60%;
    }

    #progress-log {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }

    DataTable {
        height: 1fr;
        border: solid $primary;
    }

    RichLog {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }

    Input {
        width: 100%;
        margin: 1 0;
    }

    RadioSet {
        margin: 1 0;
    }

    Label#target-label, Label#auth-label, Label#vis-label,
    Label#provider-label, Label#count-label {
        color: $text-muted;
    }

    Label#warning-label {
        color: $warning;
        text-style: italic;
    }

    Button {
        min-width: 20;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
    ]

    # State
    provider: str = ""
    target: str = ""
    token: Optional[str] = None
    visibility: str = "all"
    selected_tags: List[str] = []

    def on_mount(self) -> None:
        clear_sensitive_env()
        self.push_screen(MainMenuScreen())

    def action_quit(self) -> None:
        cleanup_cloned_repos()
        cleanup_batch_files()
        self.exit()


def main():
    """Entry point for the TUI application."""
    app = RepoAnalysisApp()
    app.run()


if __name__ == "__main__":
    main()