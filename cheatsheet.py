from functools import cached_property
from itertools import zip_longest
from typing import Iterable
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.widget import Widget
from textual.widgets import DataTable


class CheatSheet(DataTable):
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
        self.add_columns(Text("Key", justify="right"))
        self.add_column("Action")
        self.cursor_type = "row"
        self.can_focus = False

        self.border_title = "Cheatsheet"

        filtered_binds: list[Binding] = list(filter(lambda b: type(b) == Binding and b.show, self.bindings))  # type: ignore

        l = len(filtered_binds)

        if l < 10:
            for binding in filtered_binds:
                self.add_binding(binding)
        else:
            self.add_column(Text("Key", justify="right"))
            self.add_column("Action")

            # ensure the are always more entries on the right
            split = l // 2 + 1 if l % 2 == 1 else l // 2

            for b1, b2 in zip_longest(
                filtered_binds[:split],
                filtered_binds[split:],
                fillvalue=None,
            ):
                self.add_binding_pair(b1, b2)  # type: ignore

    def add_binding(self, b: Binding) -> None:
        display = b.key
        if b.key_display:
            display = b.key_display

        self.add_row(
            Text.from_markup(f"[b]{display}[/]", justify="right"),
            Text.from_markup(b.description, justify="left"),
        )

    def add_binding_pair(self, b1: Binding | None, b2: Binding | None):
        print(f"**************** {b1} {b2}")
        if b1:
            display1 = b1.key_display if b1.key_display else b1.key
            desc1 = b1.description
        else:
            display1 = ""
            desc1 = ""

        if b2:
            display2 = b2.key_display if b2.key_display else b2.key
            desc2 = b2.description
        else:
            display2 = ""
            desc2 = ""

        self.add_row(
            Text.from_markup(f"[b]{display1}[/]", justify="right"),
            Text.from_markup(desc1, justify="left"),
            Text.from_markup(f"[b]{display2}[/]", justify="right"),
            Text.from_markup(desc2, justify="left"),
        )
