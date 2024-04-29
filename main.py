import app
import os
from rich import print


def passstore_exists():
    pass_dir = os.getenv("PASSWORD_STORE_DIR")
    if pass_dir is None:
        pass_dir = os.path.expanduser("~/.password-store")
    return os.path.isdir(pass_dir)


def decrypt():
    print("Decrypting")


def open_pass_store():
    decrypt()
    pass


def load_theme():
    print("Loading autumn theme")


def read_config():
    # finds pass store if it exists
    # reads config file if it exists
    print("Reading user config")


if __name__ == "__main__":
    if passstore_exists():
        read_config()
        open_pass_store()
        pass_app = app.Pass()
        pass_app.run()
    else:
        print(
            "[bold red]Error: Failed to find the password store.[/bold red]\n"
            "Try running '[bold]pass init[/bold]' or ensure the [bold]PASSWORD_STORE_DIR[/bold] is set."
        )
