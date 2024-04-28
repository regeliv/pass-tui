from __future__ import annotations
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.screen import Screen, ModalScreen
from textual.widgets import Placeholder, Footer, Button, DataTable, Static, Label
from textual.widgets.data_table import CellType, Row, RowKey

from textual.css.query import NoMatches


from dataclasses import dataclass
from typing import Iterator

class Header(Placeholder):
    DEFAULT_CSS= """
    Header {
        height: 1;
        dock: top;
    }
    """

class DeleteDialog(ModalScreen):
    DEFAULT_CSS="""
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
        color: red;
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
        height: 11;
        border: thick $background 80%;
        background: $surface;
    }
    """

    BINDINGS = [("escape", "leave", "Leave and don't delete"),
                ("enter", "delete", "Delete selected entries")]
    
    table: PassTable

    def __init__(self, table: PassTable , name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        self.table = table
        super().__init__(name, id, classes)

    def compose(self):
        yield Vertical(
            Label("Are you sure you want to delete the following?", id="question"),
            # TODO: add scrolling and centering
            *[Static(str(row)) for row in self.table.selected_rows],
            Static("THIS ACTION IS IRREVERSIBLE!", id="warning"),
            Static("<enter> to confirm, <esc> to exit", id="confirm"),
            id="dialog",
        )

    def action_leave(self):
        self.app.pop_screen()

    def action_delete(self):
        self.app.pop_screen()
        # TODO: self.app.delete()



class Sidebar(Vertical):
    DEFAULT_CSS= """
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
    ["Profile",     "Category",     "URL"],
    ["school",      "",             "office.com"],
    ["learning",    "typing",       "keybr.com"],
    ["learing",     "",             "khanacademy.org"]
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

    def __str__(self) -> str:
        """Returns the path representation of a password entry"""
        # FIXME: spurious slash if category is empty
        return "/".join([path_fragment for path_fragment in self.pass_data])

class PassTable(DataTable):
    def on_mount(self) -> None:
        self.add_column("", key="checkbox")
        self.add_columns(*passwords[0][:-1])

        # add the last column separately to be able to set its key and use it later
        # set width to zero so that auto_width is set to false
        self.last_column = self.add_column(passwords[0][-1], width=0, key=passwords[0][-1])

        self.cursor_type = "row"
        self.zebra_stripes = True

        for number, row in enumerate(passwords[1:], start=1):
            label = Text(str(number), style="#bold")
            # TODO: Extract it into a method
            row_key = self.add_row(Checkbox(), *row, label=label)
    
    def force_refresh(self) -> None:
        """Force refresh table."""
        # HACK: Without such increment, the table is refreshed
        # only when focus changes to another column.
        self._update_count += 1
        self.refresh()

    def get_cursor_row(self):
        key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        return PassRow(key=key, table=self)

    def toggle_select(self) -> None:
        self.get_cursor_row().toggle()
        self.force_refresh()

    @property
    def all_rows(self) -> Iterator[PassRow]:
        for key in self.rows:
            yield PassRow(table=self, key=key)

    @property
    def selected_rows(self) -> Iterator[PassRow]:
        for row in self.all_rows:
            if row.is_selected:
                yield row



class Pass(App):
    BINDINGS = [
        ("n", "new_entry", "New"),
        ("e", "edit_entry", "Edit"),
        ("m", "move_entry", "Move"),
        ("f", "find_entry", "Find"),
        ("F", "find_entry", "Filter"),
        ("space", "select_entry", "Select/deselect"),
        ("d", "delete_entry",  "Delete"),
        ("p", "copy_password", "Copy password"),
        ("u", "copy_username", "Copy username"),
        ("t", "toggle_dark", "Dark/light mode"),
        ("q", "quit", "Quit")
    ]

    def action_delete_entry(self) -> None:
        try:
            self.push_screen(DeleteDialog(self.table))
        except NoMatches:
            return


    @property
    def table(self) -> PassTable:
        """Get PassTable, throws NoMatches exception if it's not in the current
           screen
        """
        return self.query_one("#passtable", PassTable)

    def action_select_entry(self) -> None:
        try:
            table = self.query_one(PassTable)
            table.toggle_select()
        except:
            return

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield PassTable(id="passtable")
            yield Sidebar()

    def __resize_pass_table(self) -> None:
        """
        Expands the last column in the password table to fill the whole
        remaining table space
        """
        try:
            # TODO: change to method access
            table = self.query_one("#passtable", PassTable)
        except NoMatches:
            return

        # TODO: Move this to pass table
        size = table.size
        # calculate width of all columns except the last
        total_column_width = 0
        for column in table.columns.values():
            if column.key != table.last_column.value:
                total_column_width += column.width

        # expand the last column to fit the whole table
        table.columns[table.last_column].width = size.width - total_column_width
        table.refresh()

    def post_display_hook(self):
        self.__resize_pass_table()
