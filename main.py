import app
import passutils
from rich import print


def read_config():
    # finds pass store if it exists
    # reads config file if it exists
    print("Reading user config")


if __name__ == "__main__":
    if passutils.passstore_exists():
        read_config()
        pass_app = app.Pass()
        pass_app.run()
    else:
        print(
            "[bold red]Error: Failed to find the password store.[/bold red]\n"
            "Try running '[bold]pass init[/bold]' or ensure the [bold]PASSWORD_STORE_DIR[/bold] is set."
        )
