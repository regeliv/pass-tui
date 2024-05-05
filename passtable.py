from __future__ import annotations
from rich.text import Text

from textual import work
from textual.binding import Binding
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.widgets import (
    DataTable,
)

from typing import Iterator
import os

from cheatsheet import CheatSheet
import passutils
from passutils import PassTuple
from passrow import PassRow, RowCheckbox
from screens import (
    DeleteDialog,
    FindScreen,
    MoveDialog,
    NewEntryDialog,
    NewEntryTuple,
    RenameDialog,
)


class PassTable(DataTable):
    BINDINGS = [
        Binding("n", "new_entry", "Add new password"),
        Binding("d", "delete_entry", "Delete password"),
        Binding("e", "edit_entry", "Edit password"),
        Binding("m", "move_entry", "Move password"),
        Binding("f,/", "find", "Find a password"),
        Binding("R", "rename", "Rename password"),
        Binding("p", "copy_password", "Copy password"),
        Binding("u", "copy_username", "Copy username"),
        Binding("space", "select_entry", "Select/deselect", key_display="<spc>"),
        Binding("shift+up", "select_up", "Select many up", key_display="shift+↑"),
        Binding("shift+down", "select_down", "Select many down", key_display="shift+↓"),
        Binding("ctrl+up", "deselect_up", "Deselect many up", key_display="ctrl+↑"),
        Binding(
            "ctrl+down", "deselect_down", "Deselect many down", key_display="ctrl+↓"
        ),
        Binding("escape", "escape", "Deselect all", key_display="<esc>"),
        Binding("a", "select_all", "Select all entries"),
        Binding("r", "reverse_selection", "Reverse selection"),
        Binding("h", "toggle_help", "Toggle help", priority=True),
    ]

    def sort_sync_enumerate(self) -> None:
        self.sort(key=lambda row: (row[1], row[2], row[3]))
        self.sync()
        self.update_enumeration()

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

    def action_escape(self) -> None:
        try:
            cheatsheet = self.app.query_one(CheatSheet)
            cheatsheet.remove()
        except NoMatches:
            self.deselect_all()

    def action_toggle_help(self) -> None:
        try:
            cheatsheet = self.app.query_one(CheatSheet)
            cheatsheet.remove()
        except NoMatches:
            screen = self.app.query_one("#main-screen", expect_type=Vertical)
            screen.mount(CheatSheet(self.BINDINGS))

    @work
    async def action_rename(self) -> None:
        if self.row_count <= 0:
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
        if self.row_count <= 0:
            return

        return_code = passutils.passcli_copy(self.current_row.pass_tuple, 1)

        if return_code != 0:
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
        if self.row_count <= 0:
            return

        return_code = passutils.passcli_copy(self.current_row.pass_tuple, 2)

        if return_code != 0:
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
    async def action_move_entry(self) -> None:
        if self.row_count <= 0:
            return

        move, keep_cats, dst = await self.app.push_screen_wait(
            MoveDialog(self.selected_rows)
        )
        if not move:
            return
        self.move(dst, keep_cats)

    @work
    async def action_new_entry(self) -> None:
        new_entry = await self.app.push_screen_wait(NewEntryDialog())
        if new_entry.create:
            self.insert(new_entry)

    @work
    async def action_find(self) -> None:
        if self.row_count <= 0:
            return

        path = await self.app.push_screen_wait(FindScreen(self.all_rows))
        self.select(path)

    @work
    async def action_delete_entry(self) -> None:
        if self.row_count <= 0:
            return

        if await self.app.push_screen_wait(DeleteDialog(self.selected_rows)):
            self.delete_selected()

    def action_edit_entry(self) -> None:
        if self.row_count <= 0:
            return

        with self.app.suspend():
            passutils.passcli_edit(self.current_row.pass_tuple)

    def deselect_all(self) -> None:
        for row in self.all_rows:
            row.deselect()

        self.force_refresh()

    def action_select_all(self) -> None:
        for row in self.all_rows:
            row.select()

        self.force_refresh()

    def action_reverse_selection(self) -> None:
        for row in self.all_rows:
            row.toggle()

        self.force_refresh()

    def action_select_up(self) -> None:
        if self.row_count <= 0:
            return

        self.current_row.select()
        super().action_cursor_up()
        self.current_row.select()

        self.force_refresh()

    def action_select_down(self) -> None:
        if self.row_count <= 0:
            return

        self.current_row.select()
        super().action_cursor_down()
        self.current_row.select()

        self.force_refresh()

    def action_deselect_up(self) -> None:
        if self.row_count <= 0:
            return

        self.current_row.deselect()
        super().action_cursor_up()
        self.current_row.deselect()

        self.force_refresh()

    def action_deselect_down(self) -> None:
        if self.row_count <= 0:
            return
        self.current_row.deselect()
        super().action_cursor_down()
        self.current_row.deselect()

        self.force_refresh()

    def action_select_entry(self) -> None:
        if self.row_count <= 0:
            return

        self.current_row.toggle()
        self.force_refresh()

    def delete_selected(self) -> None:
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
        pass_tuple = PassTuple.from_str(pass_str)
        for row in self.all_rows:
            if row.pass_tuple == pass_tuple:
                print("Matched!")

                self.move_cursor(row=self.get_row_index(row.key))
                return

    def update_enumeration(self) -> None:
        for number, row in enumerate(self.ordered_rows, start=1):
            row.label = Text(str(number), style="#bold", justify="right")

    def force_refresh(self) -> None:
        """Force refresh table."""
        # HACK: Without such increment, the table is refreshed
        # only when focus changes to another column.
        self._update_count += 1
        self.refresh()

    def sync(self) -> None:
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

    def insert(self, new_entry: NewEntryTuple):
        pass_tuple = PassTuple.from_str(os.path.join(new_entry.prof_cat, new_entry.url))

        if passutils.passcli_insert(pass_tuple, new_entry.username, new_entry.password):
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

    def move(self, dst: str, keep_cats: bool) -> None:
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
        key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        return PassRow(key=key, table=self)

    @property
    def all_rows(self) -> Iterator[PassRow]:
        return map(lambda row: PassRow(table=self, key=row.key), self.ordered_rows)

    @property
    def selected_rows(self) -> Iterator[PassRow]:
        count = 0
        for row in self.all_rows:
            if row.is_selected:
                count += 1
                yield row

        if count == 0:
            yield self.current_row

    @property
    def selected_tuples(self) -> Iterator[PassTuple]:
        count = 0
        for row in self.all_rows:
            if row.is_selected:
                count += 1
                yield row.pass_tuple

        if count == 0:
            yield self.current_row.pass_tuple
