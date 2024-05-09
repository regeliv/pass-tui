from __future__ import annotations
from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.widgets import DataTable

import os
from typing import Iterator

from cheatsheet import CheatSheet
import passutils
from passutils import PassTuple
from passrow import PassRow, RowCheckbox
from dialogs import (
    DeleteDialog,
    FindScreen,
    MoveDialog,
    NewEntryDialog,
    NewEntryTuple,
    RenameDialog,
)


class PassTable(DataTable):
    """DataTable with functions to allow handling passwords
    stored in a pass store.
    """

    BINDINGS = [
        Binding("n", "new", "Add new password"),
        Binding("d", "delete", "Delete password"),
        Binding("e", "edit", "Edit password"),
        Binding("m", "move", "Move password"),
        Binding("f,/", "find", "Find a password"),
        Binding("R", "rename", "Rename password"),
        Binding("p", "copy_password", "Copy password"),
        Binding("u", "copy_username", "Copy username"),
        Binding("k", "cursor_up", "Move up", show=False),
        Binding("j", "cursor_down", "Move down", show=False),
        Binding("space", "select_entry", "Select/deselect", key_display="<spc>"),
        Binding("shift+up,K", "select_up", "Select many up", key_display="shift+↑"),
        Binding(
            "shift+down,J",
            "select_down",
            "Select many down",
            key_display="shift+↓",
        ),
        Binding(
            "ctrl+up,ctrl+k", "deselect_up", "Deselect many up", key_display="ctrl+↑"
        ),
        Binding(
            "ctrl+down,ctrl+j",
            "deselect_down",
            "Deselect many down",
            key_display="ctrl+↓",
        ),
        Binding("escape", "escape", "Deselect all", key_display="<esc>"),
        Binding("a", "select_all", "Select all entries"),
        Binding("r", "reverse_selection", "Reverse selection"),
        Binding("h", "toggle_help", "Toggle help", priority=True),
    ]

    def on_mount(self) -> None:
        self.border_title = Text.from_markup("[b][N]ew | [D]elete | [E]dit[/]")
        self.border_subtitle = Text.from_markup(
            "[b][M]ove | [F]ind | [H]elp | [Q]uit[/]"
        )

        self.add_column("", key="checkbox")
        self.add_column("Profile", key="Profile")
        self.add_column("Category", key="Category")
        self.add_column("URL", key="URL")

        self.cursor_type = "row"

        self.sort_sync_enumerate()
        self.set_interval(5, self.sort_sync_enumerate)

    def sync(self) -> None:
        """Synchronize entries in the data table
        to those in the filesystem, moving the cursor as
        necessary.
        """
        new_passes = passutils.get_categorized_passwords()
        synced_passes = []
        old_passes = list(self.all_rows)
        i, j = 0, 0

        old_cursor = self.cursor_row
        cursor_diff = 0

        while i < len(new_passes) and j < len(old_passes):
            new_tuple = new_passes[i]
            old_pass = old_passes[j]

            if new_tuple < old_pass.pass_tuple:
                synced_passes.append((RowCheckbox(), *new_tuple))
                i += 1
                cursor_diff += 1
            elif new_tuple > old_pass.pass_tuple:
                j += 1
                cursor_diff -= 1
            else:
                synced_passes.append((old_pass.checkbox, *new_tuple))
                i += 1
                j += 1

        while i < len(new_passes):
            synced_passes.append((RowCheckbox(), *new_passes[i]))
            i += 1

        self.clear()
        for row in synced_passes:
            self.add_row(*row)

        self.move_cursor(row=old_cursor + cursor_diff)

    def update_enumeration(self) -> None:
        """Update row numbers to agree with the order
        they are shown in the data table.
        """
        for number, row in enumerate(self.ordered_rows, start=1):
            row.label = Text(str(number), style="#bold", justify="right")

    def sort_sync_enumerate(self) -> None:
        """Sort the entries in the table,
        synchronize them with the filesystem and
        update row numbers.
        """
        self.sort(key=lambda row: (row[1], row[2], row[3]))
        self.sync()
        self.update_enumeration()

    def deselect_all(self) -> None:
        """Remove selection from all rows."""
        for row in self.all_rows:
            row.deselect()

        self.force_refresh()

    def delete_selected(self) -> None:
        """Delete rows tha are selected, notify user of the outcome"""
        selected_rows = list(self.selected_rows)
        n_fails = 0
        for row in selected_rows:
            n_fails += not passutils.rm(row.pass_tuple)
        if n_fails > 0:
            self.notify(
                f"Failed to remove {n_fails} passwords.",
                title="Removal failure",
                severity="warning",
            )
        else:
            self.notify("Removal succeeded.", title="Success!")

        passutils.prune()
        self.sort_sync_enumerate()

    def select(self, pass_str: str) -> None:
        """Move cursor to the chosen entry.

        Args:
            pass_str: a relative pass store path
        """

        pass_tuple = PassTuple.from_str(pass_str)
        for row in self.all_rows:
            if row.pass_tuple == pass_tuple:
                print("Matched!")

                self.move_cursor(row=self.get_row_index(row.key))
                return

    def force_refresh(self) -> None:
        """Force refresh table."""
        # HACK: Without such increment, the table is refreshed
        # only when focus changes to another column.
        self._update_count += 1
        self.refresh()

    def insert(self, new_entry: NewEntryTuple):
        """Create a password from the data in the new_entry tuple.
        Notifies user of the outcome.

        Args:
            new_entry: a tuple with data that is to be inserted
            into the password file.
        """
        pass_tuple = PassTuple.from_str(os.path.join(new_entry.prof_cat, new_entry.url))

        if passutils.passcli_insert(pass_tuple, new_entry.username, new_entry.password):
            success = True
        else:
            success = False

        if success:
            self.notify(
                "Password insertion succeeded.",
                title="Success!",
            )
        else:
            self.notify(
                "Password insertion failed.",
                title="Insertion failure",
                severity="error",
            )

        self.sort_sync_enumerate()
        if success:
            self.select(str(pass_tuple))

    def move(self, dst: str, keep_cats: bool) -> None:
        """Move selected entries to destination, optionally
        preserving category hierarchy. Notify the user
        of the outcome.

        Args:
            dst: destination directory, if it's an
            empty string the passwords will be moved to
            the root directory
            keep_cats: whether to preserve categories, if False
            the parent of each password entry will be the dst directory

        """
        change_list_rows: list[PassRow] = list(self.selected_rows)
        if passutils.move_has_conflicts(self.selected_tuples, dst, keep_cats):
            self.notify(
                "Conflicts detected, resolve them before moving.",
                title="Failed to move passwords",
                severity="error",
            )
            return

        n_fails = 0

        # code repetition to avoid ckecking keep_cats in each iteration
        if keep_cats:
            for row in change_list_rows:
                _, cats, url = row.pass_tuple
                ok = passutils.move(
                    row.pass_tuple,
                    os.path.join(dst, cats),
                )
                n_fails += not ok
                if ok:
                    row.update(PassTuple.from_str(os.path.join(dst, cats, url)))
        else:
            for row in change_list_rows:
                _, cats, url = row.pass_tuple
                ok = passutils.move(row.pass_tuple, dst)
                n_fails += not ok
                if ok:
                    row.update(PassTuple.from_str(os.path.join(dst, url)))

        self.sort_sync_enumerate()

        if n_fails == 0:
            self.notify("Move succeeded.", title="Success!")
        else:
            self.notify(
                f"Failed to move {n_fails} password(s).",
                title="Partial Failure",
                severity="warning",
            )

        passutils.prune()
        self.sort_sync_enumerate()

    @property
    def current_row(self) -> PassRow:
        """The row pointed to by the user's cursor."""
        key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        return PassRow(key=key, table=self)

    @property
    def all_rows(self) -> Iterator[PassRow]:
        """All rows in the data table."""
        return map(lambda row: PassRow(table=self, key=row.key), self.ordered_rows)

    @property
    def selected_rows(self) -> Iterator[PassRow]:
        """Rows that were selected by the user.
        If none were selected current row is yielded.
        """
        count = 0
        for row in self.all_rows:
            if row.is_selected:
                count += 1
                yield row

        if count == 0:
            yield self.current_row

    @property
    def selected_tuples(self) -> Iterator[PassTuple]:
        """Tuples corresponding to all rows that were
        selected by the user.
        """
        count = 0
        for row in self.all_rows:
            if row.is_selected:
                count += 1
                yield row.pass_tuple

        if count == 0:
            yield self.current_row.pass_tuple

    def action_escape(self) -> None:
        """If the cheatsheet is on, close cheatsheet.
        Otherwise, deselect all rows.
        """
        try:
            cheatsheet = self.app.query_one(CheatSheet)
            cheatsheet.remove()
        except NoMatches:
            self.deselect_all()

    def action_toggle_help(self) -> None:
        """Toggle the cheatsheet."""
        try:
            cheatsheet = self.app.query_one(CheatSheet)
            cheatsheet.remove()
        except NoMatches:
            screen = self.app.query_one("#main-screen", expect_type=Vertical)
            screen.mount(CheatSheet(self.BINDINGS))

    @work
    async def action_rename(self) -> None:
        """Rename the password under the cursor."""
        if self.row_count <= 0:
            self.notify(
                "No passwords in database.", title="Rename failed!", severity="warning"
            )
            return

        pass_tuple = self.current_row.pass_tuple

        new_name = await self.app.push_screen_wait(RenameDialog(pass_tuple))

        if new_name is None:
            return

        if not passutils.rename(pass_tuple, new_name):
            self.notify(
                "Failed to rename the password.",
                title="Renaming failed!",
                severity="error",
            )
            return

        self.notify("Rename succeeded.", title="Success!")
        passutils.prune()
        self.sort_sync_enumerate()
        self.select(str(PassTuple(pass_tuple.profile, pass_tuple.cats, new_name)))

    def action_copy_password(self) -> None:
        """Copy the password under the cursor."""
        if self.row_count <= 0:
            self.notify(
                "No passwords in database.", title="Copy failed!", severity="warning"
            )
            return

        ok = passutils.passcli_copy(self.current_row.pass_tuple, 1)

        if not ok:
            self.notify(
                "Ensure the password field exists.",
                title="Copy failed!",
                severity="error",
            )
        else:
            self.notify(
                f"Password will be cleared in {passutils.get_password_clear_time()} seconds.",
                title="Password copied!",
            )

    def action_copy_username(self) -> None:
        """Copy the username under the cursor."""
        if self.row_count <= 0:
            self.notify(
                "No passwords in database.", title="Copy failed!", severity="warning"
            )
            return

        ok = passutils.passcli_copy(self.current_row.pass_tuple, 2)

        if not ok:
            self.notify(
                "Ensure the username field exists.",
                title="Copy failed!",
                severity="error",
            )
        else:
            self.notify(
                f"Username will be cleared in {passutils.get_password_clear_time()} seconds.",
                title="Username copied!",
            )

    @work
    async def action_move(self) -> None:
        """Move selected passwords."""
        if self.row_count <= 0:
            self.notify(
                "No passwords selected in database.",
                title="Move failed!",
                severity="warning",
            )
            return

        move, keep_cats, dst = await self.app.push_screen_wait(
            MoveDialog(self.selected_rows)
        )
        if not move:
            return
        self.move(dst, keep_cats)

    @work
    async def action_new(self) -> None:
        """Create a new password."""
        new_entry = await self.app.push_screen_wait(NewEntryDialog())
        if new_entry.create:
            self.insert(new_entry)

    @work
    async def action_find(self) -> None:
        """Open fuzzy search."""
        if self.row_count <= 0:
            self.notify(
                "No passwords in database.", title="Find failed!", severity="warning"
            )
            return

        path = await self.app.push_screen_wait(FindScreen(self.all_rows))
        self.select(path)

    @work
    async def action_delete(self) -> None:
        """Delete selected passwords."""
        if self.row_count <= 0:
            self.notify(
                "No passwords in database.", title="Delete failed!", severity="warning"
            )
            return

        if await self.app.push_screen_wait(DeleteDialog(self.selected_rows)):
            self.delete_selected()

    def action_edit(self) -> None:
        """Edit selected passwords."""
        if self.row_count <= 0:
            self.notify(
                "No passwords in database.", title="Edit failed!", severity="warning"
            )
            return

        with self.app.suspend():
            passutils.passcli_edit(self.current_row.pass_tuple)

    def action_select_all(self) -> None:
        """Select all passwords in the table."""
        for row in self.all_rows:
            row.select()

        self.force_refresh()

    def action_reverse_selection(self) -> None:
        """Select all passwords that are not selected and
        deselect all that are.
        """
        for row in self.all_rows:
            row.toggle()

        self.force_refresh()

    def action_select_up(self) -> None:
        """Select all passwords the cursor is touching
        while moving up.
        """
        if self.row_count <= 0:
            return

        self.current_row.select()
        super().action_cursor_up()
        self.current_row.select()

        self.force_refresh()

    def action_select_down(self) -> None:
        """Select all passwords the cursor is touching
        while moving down.
        """
        if self.row_count <= 0:
            return

        self.current_row.select()
        super().action_cursor_down()
        self.current_row.select()

        self.force_refresh()

    def action_deselect_up(self) -> None:
        """Deselect all passwords the cursor is touching
        while moving up.
        """
        if self.row_count <= 0:
            return

        self.current_row.deselect()
        super().action_cursor_up()
        self.current_row.deselect()

        self.force_refresh()

    def action_deselect_down(self) -> None:
        """Deselect all passwords the cursor is touching
        while moving down.
        """
        if self.row_count <= 0:
            return
        self.current_row.deselect()
        super().action_cursor_down()
        self.current_row.deselect()

        self.force_refresh()

    def action_select_entry(self) -> None:
        """Select the password under the cursor."""
        if self.row_count <= 0:
            return

        self.current_row.toggle()
        self.force_refresh()
