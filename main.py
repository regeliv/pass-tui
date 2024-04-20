from time import sleep
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Static, DataTable

class Pass(App):
    CSS_PATH="styles.css"
    BINDINGS = [("d","toggle_dark",  "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        yield Header()
        # yield Vertical(
        #     Static("Menu"),
        #     Button("New"),
        #     Button("Edit"),
        #     Button("Move"),
        #     id="sidebar"
        # )
        with Horizontal():
            with Vertical(id="sidebar"):
                for action in ("New", "Edit", "Move"):
                    yield Button(action, classes="menu-button")
            yield DataTable()

        
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Profile", "Category", "Website")
        table.add_rows([
            ["school", "", "office.com"],
            ["learning", "typing", "keybr.com"],
            ["learing", "", "khanacademy.org"]
            ]
        )



def passstore_exists():
    return True

def decrypt():
    print("Decrypting")

def open_pass_store():
    decrypt()
    pass

def create_pass_store():
    pass

def load_theme():
    print("Loading autumn theme")

def start_ui():
    load_theme()
    app = Pass()
    app.run()

def read_config():
    # finds pass store if it exists
    # reads config file if it exists
    print("Finding passstore")
    print("Reading user config")

if __name__ == "__main__":
    read_config()
    start_ui()
    if passstore_exists():
        open_pass_store()
    else:
        create_pass_store()

    




