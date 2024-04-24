from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.screen import Screen, ModalScreen
from textual.widgets import Placeholder, Footer, Button, DataTable, Static, Label

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

    def compose(self):
        yield Vertical(
            Label("Are you sure you want to delete the following?", id="question"),
            # TODO: add seleteced items list
            # Placeholder(),
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
    ["Profile", "Category", "Website"],
    ["school", "", "office.com"],
    ["learning", "typing", "keybr.com"],
    ["learing", "", "khanacademy.org"]
]
class PassTable(DataTable):
    def on_mount(table) -> None:
        table.add_columns(*passwords[0][:-1])

        # add the last column separately to be able to set its key and use it later
        # set width to zero so that auto_width is set to false
        table.last_column = table.add_column(passwords[0][-1], width=0, key=passwords[0][-1])

        table.cursor_type = "row"
        table.zebra_stripes = True


        for number, row in enumerate(passwords[1:], start=1):
            label = Text(str(number), style="#bold")
            table.add_row(*row, label=label)

class Pass(App):
    BINDINGS = [
        ("n", "new_entry", "New"),
        ("e", "edit_entry", "Edit"),
        ("m", "move_entry", "Move"),
        ("f", "find_entry", "Find"),
        ("F", "find_entry", "Filter"),
        ("<space>", "select_entry", "Select/unselect"),
        ("d", "delete_entry",  "Delete"),
        ("p", "copy_password", "Copy password"),
        ("u", "copy_username", "Copy username"),
        ("q", "quit", "Quit")
    ]

    def action_quit(self):
        self.app.exit()

    def action_delete_entry(self):
        self.push_screen(DeleteDialog())

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
            table = self.query_one(PassTable)
        except:
            return
        size = table.size

        # calculate width of all columns except the last
        total_column_width = 0
        for column in table.columns.values():
            if column.key != table.last_column.value:
                total_column_width += column.width

        # expand the last column to fit the whole table
        table.columns[table.last_column].width = self.size.width - total_column_width
        table.refresh()

    def post_display_hook(self):
        self.__resize_pass_table()
