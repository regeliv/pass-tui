from __future__ import annotations
from dataclasses import dataclass

from textual.widgets import DataTable
from textual.widgets.data_table import RowKey

from passutils import PassTuple


@dataclass
class RowCheckbox:
    checked: bool = False

    def __str__(self) -> str:
        return "■" if self.checked else ""

    def __rich__(self) -> str:
        return "[b]■[/]" if self.checked else ""

    def toggle(self) -> None:
        self.checked = not self.checked

    def select(self) -> None:
        self.checked = True

    def deselect(self) -> None:
        self.checked = False


@dataclass
class PassRow:
    table: DataTable
    key: RowKey

    @property
    def _data(self) -> list:
        return self.table.get_row(self.key)

    @property
    def checkbox(self) -> RowCheckbox:
        return self._data[0]

    @property
    def is_selected(self) -> bool:
        return self.checkbox.checked

    @property
    def pass_tuple(self) -> PassTuple:
        """Returns the tuple containing password metadata"""
        return PassTuple(*self._data[1:])

    @property
    def pass_data(self) -> list[str]:
        """Returns the list containing password metadata"""
        return self._data[1:]

    @property
    def profile(self) -> str:
        return self.pass_data[0]

    @property
    def cats(self) -> str:
        return self.pass_data[1]

    @property
    def url(self) -> str:
        return self.pass_data[2]

    def update(self, pass_tuple: PassTuple) -> None:
        profile, cats, url = pass_tuple
        self.table.update_cell(self.key, "Profile", profile)
        self.table.update_cell(self.key, "Category", cats)
        self.table.update_cell(self.key, "URL", url)

    def toggle(self) -> None:
        self.checkbox.toggle()

    def select(self) -> None:
        self.checkbox.select()

    def deselect(self) -> None:
        self.checkbox.deselect()

    def __str__(self) -> str:
        """Returns the path representation of a password entry"""
        # TODO: use os.path.join
        return "/".join(
            [path_fragment for path_fragment in self.pass_tuple if path_fragment != ""]
        )
