from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Placeholder, Footer, Button, DataTable

class Header(Placeholder):
    DEFAULT_CSS= """
    Header {
        height: 1;
        dock: top;
    }
    """

class Sidebar(Vertical):
    DEFAULT_CSS= """
    Sidebar {
        dock: left;
        width: 15; 
    }
    """

    def compose(self) -> ComposeResult:
        for action in ("New", "Edit", "Move"):
            yield Button(action, classes="menu-button")

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

class MainScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Horizontal():
            yield PassTable(id="passtable")
            yield Sidebar()

    def resize_pass_table(self) -> None:
        """
        Expands the last column in the password table to fill the whole
        remaining table space
        """
        table = self.query_one(PassTable)
        size = table.size

        # calculate width of all columns except the last
        total_column_width = 0
        for column in table.columns.values():
            if column.key != table.last_column.value:
                total_column_width += column.width

        # expand the last column to fit the whole table
        table.columns[table.last_column].width = self.size.width - total_column_width
        table.refresh()




class Pass(App):
    BINDINGS = [
        ("d","toggle_dark",  "Toggle dark mode"),
        ("m", "move_entry", "Move entry"),
        ("e", "edit_entry", "Edit entry"),
        ("n", "new_entry", "New entry"),
        ("f", "find_entry", "Find"),
        ("p", "copy_password", "Copy password"),
        ("u", "copy_username", "Copy username"),
    ]

    SCREENS = { "Main": MainScreen(id="main-screen") }


    def on_mount(self) -> None:
         self.push_screen("Main")


    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def post_display_hook(self):
        screen = self.children[0]
        if screen.id == "main-screen":
            screen.resize_pass_table()

