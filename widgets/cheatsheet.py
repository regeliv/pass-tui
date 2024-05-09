from typing import Tuple
from rich.text import Text
from textual.binding import Binding, BindingType
from textual.widget import Widget
from textual.widgets import DataTable
import math


class CheatSheet(DataTable):
    """A cheatsheet widgets, shows all bindings
    that are of the type Binding in a table form.
    """

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
        self.cursor_type = "row"
        self.can_focus = False

        self.border_title = "Cheatsheet"

        self.add_bindings()
        return

    @staticmethod
    def bind_to_pair(b: Binding) -> Tuple[Text, Text]:
        """Convert a Binding to a pair of Text objects

        Args:
            b: a Binding

        Returns:
            A tuple of two Text objects, whose first field
            is the Binding's bolded key_display if it is set,
            otherwise it is the Binding's key. The second
            field is the description of the Binding.
        """
        key_str = b.key_display if b.key_display else b.key
        return (
            Text.from_markup(f"[b]{key_str}[/]", justify="right"),
            Text.from_markup(f"{b.description}", justify="left"),
        )

    def add_bindings(self) -> None:
        """Add bindings, organized in a few columns"""
        filtered_binds: list[Binding] = list(filter(lambda b: type(b) == Binding and b.show, self.bindings))  # type: ignore

        l = len(filtered_binds)
        lists_of_binds = []

        rows = 7

        cols = math.ceil(l / rows)
        for _ in range(cols):
            self.add_column(Text("Key", justify="right"))
            self.add_column("Action")

        lists_of_binds = [filtered_binds[i::rows] for i in range(rows)]

        for binding_group in lists_of_binds:
            pairs = map(
                CheatSheet.bind_to_pair,
                binding_group,
            )
            self.add_row(*[item for pair in pairs for item in pair])
