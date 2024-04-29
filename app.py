from __future__ import annotations
from rich.text import Text, TextType

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Placeholder, DataTable, Static, Label
from textual.widgets.data_table import CellType, RowKey

from textual.css.query import NoMatches


from dataclasses import dataclass
from typing import Iterator


class Header(Placeholder):
    DEFAULT_CSS = """
    Header {
        height: 1;
        dock: top;
    }
    """


class DeleteDialog(ModalScreen):
    DEFAULT_CSS = """
    DeleteDialog {
        align: center middle;
    }
    #question {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #confirm {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #warning {
        color: $error;
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 20; 
        border: thick $background 80%;
        background: $surface;
    }
    #entry-list {
        column-span: 2;
        height: 5fr;
        width: 1fr;
        background: $panel
    }
    """

    BINDINGS = [
        ("escape", "leave", "Leave and don't delete"),
        ("q", "leave", "Leave and don't delete"),
        ("enter", "delete", "Delete selected entries"),
    ]

    table: PassTable

    def __init__(
        self,
        table: PassTable,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.table = table
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Are you sure you want to delete the following?", id="question"),
            VerticalScroll(
                *[Static(str(row)) for row in self.table.selected_rows],
                id="entry-list",
            ),
            Static("THIS ACTION IS IRREVERSIBLE!", id="warning"),
            Static("<enter> to confirm, <esc> to exit", id="confirm"),
            id="dialog",
        )

    def action_leave(self):
        self.app.pop_screen()

    def action_delete(self):
        self.table.delete_selected()
        self.app.pop_screen()


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


passwords = [
    ["Profile", "Category", "URL"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learning", "", "khanacademy.org"],
]


@dataclass
class Checkbox:
    checked: bool = False

    def __str__(self) -> str:
        return "■" if self.checked else ""

    def __rich__(self) -> str:
        return "[b]■[/]" if self.checked else ""

    def toggle(self) -> None:
        self.checked = not self.checked

    def select(self) -> None:
        self.checked = True

    def deselect(self) -> None:
        self.checked = False


@dataclass
class PassRow:
    table: PassTable
    key: RowKey

    @property
    def _data(self) -> list:
        return self.table.get_row(self.key)

    @property
    def checkbox(self) -> Checkbox:
        return self._data[0]

    @property
    def is_selected(self) -> bool:
        return self.checkbox.checked

    @property
    def pass_data(self) -> list:
        """Returns the list containing password metadata"""
        return self._data[1:]

    def toggle(self) -> None:
        self.checkbox.toggle()

    def select(self) -> None:
        self.checkbox.select()

    def deselect(self) -> None:
        self.checkbox.deselect()

    def __str__(self) -> str:
        """Returns the path representation of a password entry"""
        return "/".join(
            [path_fragment for path_fragment in self.pass_data if path_fragment != ""]
        )


class PassTable(DataTable):
    DEFAULT_CSS = """
        PassTable {
            scrollbar-background: $surface;
            scrollbar-background-hover: $surface;
            scrollbar-background-active: $surface;
            scrollbar-color: $surface;
            scrollbar-color-active: $surface;
            scrollbar-color-hover: $surface;
            scrollbar-corner-color: $surface;
        }
        PassTable > .datatable--cursor {
            background: $surface;
            color: #d75fd7; /* ansi 256-bit orchid */
        }

        PassTable > .datatable--hover {
            background: $surface;
        }

        PassTable > .datatable--header {
            background: $surface;
        }

        PassTable > .datatable--header-cursor {
            background: $surface;
            color: #d75fd7; /* ansi 256-bit orchid */
        }

        PassTable > .datatable--header-hover {
            background: $surface;
        }
    """

    BINDINGS = [
        ("shift+up", "select_up", "Select many entries"),
        ("shift+down", "select_down", "Select many entries"),
        ("ctrl+shift+up", "deselect_up", "Select many entries"),
        ("ctrl+shift+down", "deselect_down", "Select many entries"),
        ("escape", "deselect_all", "Remove selection"),
        ("space", "select_entry", "Select/deselect"),
        ("a", "select_all", "Select all entries"),
        ("d", "delete_entry", "Delete"),
        ("r", "reverse_selection", "Reverse selection"),
    ]

    def on_mount(self) -> None:
        self.add_column("", key="checkbox")
        self.add_columns(*passwords[0])
        self.cursor_type = "row"

        for number, row in enumerate(passwords[1:], start=1):
            label = Text(str(number), justify="right")
            self.add_row(*row, label=label)

    def action_delete_entry(self) -> None:
        if self.row_count > 0:
            self.app.push_screen(DeleteDialog(self))

    def action_deselect_all(self) -> None:
        for row in self.all_rows:
            row.deselect()

        self.force_refresh()

    def action_select_all(self) -> None:
        for row in self.all_rows:
            row.select()

        self.force_refresh()

    def action_reverse_selection(self) -> None:
        for row in self.all_rows:
            row.toggle()

        self.force_refresh()

    def action_select_up(self) -> None:
        if self.row_count > 0:
            self.current_row.select()
            super().action_cursor_up()
            self.current_row.select()

            self.force_refresh()

    def action_select_down(self) -> None:
        if self.row_count > 0:
            self.current_row.select()
            super().action_cursor_down()
            self.current_row.select()

            self.force_refresh()

    def action_deselect_up(self) -> None:
        if self.row_count > 0:
            self.current_row.deselect()
            super().action_cursor_up()
            self.current_row.deselect()

            self.force_refresh()

    def action_deselect_down(self) -> None:
        if self.row_count > 0:
            self.current_row.deselect()
            super().action_cursor_down()
            self.current_row.deselect()

            self.force_refresh()

    def action_select_entry(self) -> None:
        if self.row_count > 0:
            self.current_row.toggle()
            self.force_refresh()

    def add_row(
        self,
        *cells: CellType,
        height: int | None = 1,
        key: str | None = None,
        label: TextType | None = None,
    ) -> RowKey:
        return super().add_row(Checkbox(), *cells, height=height, key=key, label=label)

    def delete_selected(self) -> None:
        # we cannot use the iterator in the for loop directly, because the size changes
        selected_rows = list(self.selected_rows)
        for row in selected_rows:
            self.remove_row(row.key)

        self.update_enumeration()

    def update_enumeration(self) -> None:
        for number, row in enumerate(self.ordered_rows, start=1):
            row.label = Text(str(number), style="#bold", justify="right")

    def force_refresh(self) -> None:
        """Force refresh table."""
        # HACK: Without such increment, the table is refreshed
        # only when focus changes to another column.
        self._update_count += 1
        self.refresh()

    @property
    def current_row(self) -> PassRow:
        key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        return PassRow(key=key, table=self)

    @property
    def all_rows(self) -> Iterator[PassRow]:
        for key in self.rows:
            yield PassRow(table=self, key=key)

    @property
    def selected_rows(self) -> Iterator[PassRow]:
        count = 0
        for row in self.all_rows:
            if row.is_selected:
                count += 1
                yield row

        if count == 0:
            yield self.current_row


class Pass(App):
    BINDINGS = [
        ("n", "new_entry", "New"),
        ("e", "edit_entry", "Edit"),
        ("m", "move_entry", "Move"),
        ("f", "find_entry", "Find"),
        ("F", "find_entry", "Filter"),
        ("p", "copy_password", "Copy password"),
        ("u", "copy_username", "Copy username"),
        ("t", "toggle_dark", "Dark/light mode"),
        ("q", "quit", "Quit"),
    ]

    @property
    def table(self) -> PassTable:
        """Get PassTable, throws NoMatches exception if it's not in the current
        screen
        """
        return self.query_one("#passtable", PassTable)

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield PassTable(id="passtable")
            yield Sidebar()
