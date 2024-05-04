from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Placeholder

from passtable import PassTable


class Header(Placeholder):
    DEFAULT_CSS = """
    Header {
        height: 1;
        dock: top;
    }
    """


class Pass(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield PassTable(id="passtable")
