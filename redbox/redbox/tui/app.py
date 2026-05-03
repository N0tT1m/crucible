"""redbox TUI — Textual app entry point.

Screens:
  Dashboard    — recent runs + cost + refusal rates (top-level)
  Browse       — drill into one run's results
  Plugins      — list discovered plugins by kind
  Builder      — pick payloads/target/judge, hit Run
  Live         — streaming run viewer; pushed by Builder

Without textual installed, `run_or_install_hint()` prints the install
command and exits with code 1. Tests for the data layer + pipeline
helpers don't import textual; the TUI screens themselves are smoke-
tested via Textual's Pilot when textual IS available.
"""
from __future__ import annotations

from pathlib import Path

from redbox.core.registry import registry
from redbox.core.results import ResultsStore
from redbox.payloads.loader import PayloadLoader

from .data import list_runs, results_for_run
from .pipeline import BuildSpec, run_spec


def build_app(db_path: Path | str = "redbox.sqlite"):
    """Construct the Textual App. Raises ImportError if textual is missing.

    Pulled into its own builder so tests can construct the App without
    calling `.run()` (which would block on stdin).
    """
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.screen import Screen
    from textual.widgets import (
        Button,
        DataTable,
        Footer,
        Header,
        Input,
        Label,
        Select,
        SelectionList,
        Static,
    )
    from textual.widgets.selection_list import Selection

    store = ResultsStore(db_path)

    class DashboardScreen(Screen):
        BINDINGS = [
            Binding("r", "refresh", "Refresh"),
            Binding("b", "browse",  "Browse run"),
            Binding("p", "plugins", "Plugins"),
            Binding("n", "builder", "New run"),
            Binding("q", "quit",    "Quit"),
        ]

        def compose(self) -> ComposeResult:
            yield Header()
            yield Label("redbox dashboard — recent runs ([n]ew, [b]rowse, [p]lugins, [r]efresh, [q]uit)")
            self.table = DataTable(zebra_stripes=True)
            self.table.add_columns("run_id", "started", "total", "refused", "complied", "errors")
            yield self.table
            yield Footer()

        def on_mount(self) -> None:
            self.refresh_data()

        def refresh_data(self) -> None:
            self.table.clear()
            for r in list_runs(store):
                self.table.add_row(
                    r.run_id[:12] + "…", (r.started or "")[:19],
                    str(r.total), str(r.refused), str(r.complied), str(r.errors),
                )

        def action_refresh(self) -> None:
            self.refresh_data()

        def action_browse(self) -> None:
            row = self.table.cursor_row
            if row is None or row >= self.table.row_count:
                return
            run_id = list_runs(store)[row].run_id
            self.app.push_screen(BrowseScreen(run_id))

        def action_plugins(self) -> None:
            self.app.push_screen(PluginsScreen())

        def action_builder(self) -> None:
            self.app.push_screen(BuilderScreen())

    class BrowseScreen(Screen):
        BINDINGS = [Binding("escape", "back", "Back")]

        def __init__(self, run_id: str):
            super().__init__()
            self.run_id = run_id

        def compose(self) -> ComposeResult:
            yield Header()
            yield Label(f"run {self.run_id}")
            self.table = DataTable(zebra_stripes=True)
            self.table.add_columns("payload", "model", "verdict", "conf", "snippet")
            yield self.table
            yield Footer()

        def on_mount(self) -> None:
            for r in results_for_run(store, self.run_id, limit=400):
                snippet = (r.get("response") or r.get("error") or "")[:80]
                self.table.add_row(
                    r["payload_id"][:32], r["model"][:24],
                    r["verdict"] or "—",
                    f"{r['confidence']:.2f}" if r["confidence"] is not None else "—",
                    snippet.replace("\n", " "),
                )

        def action_back(self) -> None:
            self.app.pop_screen()

    class PluginsScreen(Screen):
        BINDINGS = [Binding("escape", "back", "Back")]

        def compose(self) -> ComposeResult:
            yield Header()
            yield Label("plugins")
            yield VerticalScroll(*[
                Static(f"  [{kind}]  " + (", ".join(names) or "(none)"))
                for kind, names in registry().list().items()
            ])
            yield Footer()

        def action_back(self) -> None:
            self.app.pop_screen()

    class BuilderScreen(Screen):
        """Pick payloads + mutators + target + judge, hit Run."""
        BINDINGS = [
            Binding("escape", "back", "Back"),
            Binding("ctrl+r", "submit", "Run"),
        ]

        def compose(self) -> ComposeResult:
            yield Header()
            yield Label("Builder — pick payloads, target, judge. Ctrl+R to run.")
            payloads = PayloadLoader().all()
            self.payload_list = SelectionList[str](
                *[Selection(f"{p.id}  ({p.category})", p.id, True) for p in payloads],
            )
            from redbox.mutators import list_mutators
            self.mutator_list = SelectionList[str](
                *[Selection(name, name, False) for name in list_mutators()],
            )
            self.model = Input(value="claude-haiku", placeholder="model")
            self.base_url = Input(placeholder="base url (optional)")
            self.judge = Select(
                [("regex-refusal", "regex"), ("llm-refusal", "llm")],
                value="regex", allow_blank=False,
            )
            self.target_query = Input(
                placeholder="target query — fills {target_query} in payloads (optional)",
            )
            self.run_btn = Button("Run", id="run-btn", variant="primary")
            yield Vertical(
                Horizontal(
                    Vertical(Label("Payloads"), self.payload_list),
                    Vertical(Label("Mutators"), self.mutator_list),
                ),
                Label("Target model:"),  self.model,
                Label("Base URL:"),       self.base_url,
                Label("Judge:"),          self.judge,
                Label("Target query:"),   self.target_query,
                self.run_btn,
            )
            yield Footer()

        def _spec(self) -> BuildSpec:
            return BuildSpec(
                payload_ids=list(self.payload_list.selected),
                mutator_names=list(self.mutator_list.selected),
                model=self.model.value or "claude-haiku",
                base_url=(self.base_url.value or None),
                judge=str(self.judge.value),
                target_query=(self.target_query.value or None),
                db=str(db_path),
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "run-btn":
                self.action_submit()

        def action_submit(self) -> None:
            self.app.push_screen(LiveScreen(self._spec()))

        def action_back(self) -> None:
            self.app.pop_screen()

    class LiveScreen(Screen):
        """Streaming run viewer: each result appends a row in real time."""
        BINDINGS = [
            Binding("escape", "back", "Back"),
            Binding("d", "dashboard", "Dashboard"),
        ]

        def __init__(self, spec: BuildSpec):
            super().__init__()
            self.spec = spec
            self._done = 0
            self._refused = 0
            self._complied = 0
            self._errors = 0

        def compose(self) -> ComposeResult:
            yield Header()
            self.status = Label("starting…")
            yield self.status
            self.table = DataTable(zebra_stripes=True)
            self.table.add_columns("payload", "verdict", "conf", "ms", "snippet")
            yield self.table
            yield Footer()

        def on_mount(self) -> None:
            self.run_worker(self._do_run(), exclusive=True, name="bench")

        async def _do_run(self):
            try:
                run_id, _ = await run_spec(self.spec, on_progress=self._on_progress)
                self.status.update(
                    f"done — run {run_id[:8]}…  "
                    f"refused={self._refused}  complied={self._complied}  "
                    f"errors={self._errors}  total={self._done}"
                )
            except Exception as e:  # pragma: no cover  — runtime hot path
                self.status.update(f"failed: {type(e).__name__}: {e}")

        def _on_progress(self, result) -> None:
            verdict = result.verdict.value if result.verdict else (
                "error" if result.error else "—"
            )
            if verdict == "refused":
                self._refused += 1
            elif verdict == "complied":
                self._complied += 1
            elif verdict == "error":
                self._errors += 1
            self._done += 1
            snippet = (result.response or result.error or "").replace("\n", " ")[:80]
            self.table.add_row(
                result.payload_id[:32], verdict,
                f"{result.confidence:.2f}" if result.confidence is not None else "—",
                str(result.latency_ms), snippet,
            )
            self.status.update(
                f"running — {self._done} done "
                f"(refused={self._refused} complied={self._complied} errors={self._errors})"
            )

        def action_back(self) -> None:
            self.app.pop_screen()

        def action_dashboard(self) -> None:
            self.app.pop_screen()
            self.app.pop_screen()  # also pop Builder

    class RedboxApp(App):
        CSS = """
        Screen { padding: 1 2; }
        Label { margin-bottom: 1; }
        Input { margin-bottom: 1; }
        SelectionList { height: 12; }
        #run-btn { margin-top: 1; }
        """
        BINDINGS = [Binding("q", "quit", "Quit")]

        def on_mount(self) -> None:
            self.push_screen(DashboardScreen())

    return RedboxApp


def run_or_install_hint(db_path: Path | str = "redbox.sqlite") -> int:
    try:
        AppCls = build_app(db_path)
    except ImportError:
        print(
            "redbox tui requires Textual. Install with:\n"
            "    pip install -e .[tui]"
        )
        return 1
    AppCls().run()
    return 0
