from __future__ import annotations
from dataclasses import dataclass

from textual.widgets import DataTable
from textual.widgets.data_table import RowKey

from passutils import PassTuple


@dataclass
class RowCheckbox:
    """A checkbox field used to allow a row to be selected.

    Attributes:
        checked: whether the checkbox is selected
    """

    checked: bool = False

    def __str__(self) -> str:
        return "◌" if self.checked else ""

    def __rich__(self) -> str:
        return "[b]◌[/]" if self.checked else ""

    def toggle(self) -> None:
        self.checked = not self.checked

    def select(self) -> None:
        self.checked = True

    def deselect(self) -> None:
        self.checked = False


@dataclass
class PassRow:
    """Row of a datatable with methods facilitating
    its use in the PassTable.

    Attributes:
        table: a PassTable, the row is in
        key: the row's key in the table
    """

    table: DataTable
    key: RowKey

    @property
    def _data(self) -> list:
        """List of cells in the row."""
        return self.table.get_row(self.key)

    @property
    def checkbox(self) -> RowCheckbox:
        """The checkbox object in the row."""
        return self._data[0]

    @property
    def is_selected(self) -> bool:
        """Whether the checkbox is checked."""
        return self.checkbox.checked

    @property
    def pass_tuple(self) -> PassTuple:
        """PassTuple that corresponds to the row data"""
        return PassTuple(*self._data[1:])

    @property
    def pass_data(self) -> list[str]:
        """Row data, without the checkbox"""
        return self._data[1:]

    @property
    def profile(self) -> str:
        """The cell that corresponds to the profile field in PassTuple."""
        return self.pass_data[0]

    @property
    def cats(self) -> str:
        """The cell that corresponds to the category field in PassTuple."""
        return self.pass_data[1]

    @property
    def url(self) -> str:
        """The cell that corresponds to the url field in PassTuple."""
        return self.pass_data[2]

    def update(self, pass_tuple: PassTuple) -> None:
        """Update the row with new data.

        Args:
            pass_tuple: a PassTuple with new fields that are to be
            stored in the row.
        """
        profile, cats, url = pass_tuple
        self.table.update_cell(self.key, "Profile", profile)
        self.table.update_cell(self.key, "Category", cats)
        self.table.update_cell(self.key, "URL", url)

    def toggle(self) -> None:
        """Toggle the checkbox in the row."""
        self.checkbox.toggle()

    def select(self) -> None:
        """Select the checkbox in the row."""
        self.checkbox.select()

    def deselect(self) -> None:
        """Deselect the checkbox in the row."""
        self.checkbox.deselect()

    def __str__(self) -> str:
        """Returns the path representation of a password entry"""
        return str(self.pass_tuple)
