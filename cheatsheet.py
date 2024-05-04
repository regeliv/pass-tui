from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widget import Widget
from textual.widgets import DataTable


class CheatSheet(Widget):
    bindings: list[BindingType]

    def __init__(
        self,
        bindings: list[BindingType],
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        self.bindings = bindings
        super().__init__(
            *children, name=name, id=id, classes=classes, disabled=disabled
        )

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns(Text("Key", justify="right"))
        table.add_column("Action")
        table.cursor_type = "row"
        table.can_focus = False
        self.border_title = "Cheatsheet"
        for binding in self.bindings:
            if type(binding) == Binding:
                if binding.show:
                    if binding.key_display:
                        table.add_row(
                            Text.from_markup(
                                f"[b]{binding.key_display}[/]", justify="right"
                            ),
                            Text.from_markup(binding.description, justify="left"),
                        )
                    else:
                        table.add_row(
                            Text.from_markup(f"[b]{binding.key}[/]", justify="right"),
                            Text.from_markup(binding.description, justify="left"),
                        )

    def compose(self) -> ComposeResult:
        yield DataTable()
