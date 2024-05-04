from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Placeholder, Static

from passtable import PassTable


class Header(Widget):
    DEFAULT_CSS = """
    Header {
        height: 1;
        dock: top;
    }
    Static {
        align: center middle;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Pass", id="pass")


class Pass(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield PassTable(id="passtable")
