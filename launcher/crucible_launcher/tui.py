from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static, Tree
from textual.widgets.tree import TreeNode

from crucible_launcher import installer, runner
from crucible_launcher.registry import Tool, by_category, load_categories, load_tools

BANNER = r"""
   ___ ___ _   _  ___ ___ ___ _    ___
  / __| _ \ | | |/ __|_ _| _ ) |  | __|
 | (__|   / |_| | (__ | || _ \ |__| _|
  \___|_|_\\___/ \___|___|___/____|___|
   red-team launcher  ·  press enter to run  ·  i to install  ·  q to quit
"""


class CrucibleApp(App):
    CSS = """
    Tree { width: 50%; }
    #right { width: 50%; padding: 1 2; }
    #banner { color: #00ff9f; }
    #help { color: #888; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "run_selected", "Run"),
        Binding("i", "install_selected", "Install"),
        Binding("r", "refresh", "Reload"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.tools: list[Tool] = []
        self._selected: Tool | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield Tree("Crucible", id="tree")
            with Vertical(id="right"):
                yield Static(BANNER, id="banner")
                yield Static("", id="info")
                yield Static("enter run · i install · r reload · q quit", id="help")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Crucible"
        self.sub_title = "Parrot-style launcher"
        self._reload()

    def _reload(self) -> None:
        self.tools = load_tools()
        cats = load_categories()
        tree = self.query_one("#tree", Tree)
        tree.clear()
        tree.root.expand()
        for cat, items in by_category(self.tools).items():
            label = f"{cat}  ({len(items)})"
            node: TreeNode = tree.root.add(label, expand=True)
            if cat in cats and cats[cat]:
                node.data = {"description": cats[cat]}
            for t in items:
                marker = "✓" if installer.is_installed(t) else "·"
                node.add_leaf(f"{marker} {t.name} — {t.help}", data=t)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        data = event.node.data
        info = self.query_one("#info", Static)
        if isinstance(data, Tool):
            self._selected = data
            installed = "installed" if installer.is_installed(data) else "not installed"
            info.update(
                f"[b]{data.name}[/b]  ({installed})\n"
                f"category: {data.category}\n"
                f"command:  {data.command}\n"
                f"\n{data.help}"
            )
        else:
            self._selected = None
            info.update("")

    def action_run_selected(self) -> None:
        if not self._selected:
            return
        with self.suspend():
            runner.run(self._selected)

    def action_install_selected(self) -> None:
        if not self._selected:
            return
        with self.suspend():
            installer.install(self._selected)
        self._reload()

    def action_refresh(self) -> None:
        self._reload()


def launch() -> int:
    CrucibleApp().run()
    return 0
