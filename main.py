import app
import passutils
from rich import print

if __name__ == "__main__":
    if passutils.passstore_exists():
        pass_app = app.Pass()
        pass_app.run()
    else:
        print(
            "[bold red]Error: Failed to find the password store.[/bold red]\n"
            "Try running '[bold]pass init[/bold]' or ensure the [bold]PASSWORD_STORE_DIR[/bold] is correctly set."
        )
