from __future__ import annotations
from rich.text import Text, TextType

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, Placeholder, DataTable, Static, Label, TextArea
from textual.widgets.data_table import CellType, RowKey

from typing import Iterator

from passtable import PassTable


class Header(Placeholder):
    DEFAULT_CSS = """
    Header {
        height: 1;
        dock: top;
    }
    """


class Sidebar(Vertical):
    DEFAULT_CSS = """
    Sidebar {
        border-left: solid white;
        dock: right;
        width: 30; 
    }
    """

    def compose(self) -> ComposeResult:
        for binding in self.app.BINDINGS:
            yield Static(f"{binding[0]} - {binding[2]}")


class Pass(App):
    BINDINGS = [
        ("n", "new_entry", "New"),
        ("e", "edit_entry", "Edit"),
        ("m", "move_entry", "Move"),
        ("f", "find_entry", "Find"),
        ("F", "find_entry", "Filter"),
        ("p", "copy_password", "Copy password"),
        ("u", "copy_username", "Copy username"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield PassTable(id="passtable")
            yield Sidebar()
