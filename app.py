from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Placeholder, Static
from rich.text import Text

from passtable import PassTable


class Header(Widget):
    """Widget that shows the title."""

    def compose(self) -> ComposeResult:
        yield Static(Text.from_markup("[b]Pass[/]"), id="pass")


class Pass(App):
    """The App itself."""

    CSS_PATH = "styles.css"
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="main-screen"):
            yield Header()
            yield PassTable(id="passtable")
