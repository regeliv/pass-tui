from __future__ import annotations
from functools import cached_property
from rich.text import Text

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.containers import Vertical, VerticalScroll, Grid
from textual.validation import Length, Number
from textual.widget import Widget
from textual.widgets import (
    Input,
    DataTable,
    OptionList,
    Static,
    TabPane,
    TabbedContent,
    Checkbox,
)
from textual.widgets.data_table import RowKey

import rapidfuzz

from typing import Iterator, Iterable, Tuple
from dataclasses import dataclass
import os
import string

import passutils
from passutils import PassTuple


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


class FindScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("escape", "leave", "Leave"),
        Binding("down", "down", "Move", priority=True),
        Binding("up", "up", "", priority=True),
        Binding("enter", "select_and_leave", priority=True),
    ]

    rows: list[str]

    def __init__(
        self,
        rows: Iterable[PassRow],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.rows = [str(row) for row in rows]
        super().__init__(name, id, classes)

    @cached_property
    def option_list(self) -> OptionList:
        return self.query_one(OptionList)

    def on_mount(self) -> None:
        self.option_list.add_options(self.rows)
        self.option_list.highlighted = 0
        self.option_list.can_focus = False

    def action_down(self) -> None:
        # appeasing lsp
        if self.option_list.highlighted is not None:
            self.option_list.highlighted += 1

    def action_up(self) -> None:
        if self.option_list.highlighted is not None:
            self.option_list.highlighted -= 1

    def compose(self) -> ComposeResult:
        with Vertical(id="vertical"):
            yield Input(id="input")
            yield OptionList(id="option-list")

    @on(Input.Changed)
    def regenerate(self) -> None:
        self.option_list.clear_options()
        search_text = self.query_one(Input).value

        options = [
            match
            for match, _, _ in rapidfuzz.process.extract(
                search_text, self.rows, scorer=rapidfuzz.fuzz.WRatio, limit=None
            )
        ]
        self.option_list.add_options(options)
        self.option_list.highlighted = 0

    def action_leave(self) -> None:
        self.app.pop_screen()

    def action_select_and_leave(self) -> None:
        option_idx = self.option_list.highlighted
        # appeasing lsp, will always execute
        if option_idx is not None:
            option = str(self.option_list.get_option_at_index(option_idx).prompt)
            self.dismiss(option)


class DeleteDialog(ModalScreen[bool]):
    BINDINGS = [
        Binding("escape", "leave", "Leave without deleting", key_display="<esc>"),
        Binding("enter", "delete", "Delete", key_display="<cr>"),
    ]

    rows: list[str]

    def __init__(
        self,
        rows: Iterable[PassRow],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.rows = [str(row) for row in rows]
        super().__init__(name, id, classes)

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = "Delete"

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield VerticalScroll(
                *[Static(str(row)) for row in self.rows],
                id="entry-list",
            )
            yield Static(
                Text.from_markup("[b red]THIS ACTION IS IRREVERSIBLE![/]"), id="warning"
            )
        yield CheatSheet(self.BINDINGS)

    def action_leave(self):
        self.dismiss(False)

    def action_delete(self):
        self.dismiss(True)


class NewEntryDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "leave", "Leave without saving", key_display="<esc>"),
        Binding("tab", "focus_next", "Next", key_display="<tab>"),
        Binding("shift+tab", "focus_previous", "Previous", key_display="shift+<tab>"),
        Binding("ctrl+s", "reveal_password", "Show/hide password", key_display="^s"),
        Binding(
            "ctrl+r", "regenerate_password", "Regenerate password", key_display="^r"
        ),
        Binding(
            "ctrl+a",
            "increase_len",
            "Increase password length",
            key_display="^a",
            priority=True,
        ),
        Binding(
            "ctrl+x",
            "decrease_len",
            "Decrease password length",
            key_display="^x",
            priority=True,
        ),
    ]

    table: PassTable
    alphabet: str

    def __init__(
        self,
        table: PassTable,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.table = table
        self.alphabet = string.ascii_letters
        super().__init__(name, id, classes)

    @property
    def passfield(self) -> Input:
        return self.query_one("#password", expect_type=Input)

    @property
    def chosen_mode(self) -> str:
        return self.query_one(TabbedContent).active

    def on_mount(self) -> None:
        self.query_one("#profile-category").border_title = "profile/category"
        self.query_one("#url").border_title = "URL"
        self.query_one("#username").border_title = "username"
        self.query_one("#password").border_title = "password"
        self.query_one("#dialog").border_title = "New"
        self.query_one("#words-len").border_title = "length"
        self.query_one("#symbols-len").border_title = "length"
        self.query_one("#seps").border_title = "separators"
        self.update_alphabet()

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Input(id="profile-category", classes="input-box")
            yield Input(id="url", classes="input-box", validators=[Length(minimum=1)])
            yield Input(id="username", classes="input-box")
            yield Input(
                id="password",
                classes="input-box",
                password=True,
                validators=[
                    Length(minimum=1),
                ],
            )

            with TabbedContent(id="password-input"):
                with TabPane("Symbols", id="symbols-pane"):
                    with Grid(id="symbols"):
                        yield Input(
                            value="16",
                            id="symbols-len",
                            type="number",
                            classes="input-box",
                            validators=[Number(minimum=1)],
                            restrict="[0-9]*",
                        )
                        yield Checkbox("A-Z", id="upper", value=True)
                        yield Checkbox("a-z", id="lower", value=True)
                        yield Checkbox("0-9", id="nums", value=True)
                        yield Checkbox("/*+&...", id="punctuation", value=True)
                with TabPane("Words", id="words-pane"):
                    with Grid(id="words"):
                        yield Input(
                            id="seps",
                            valid_empty=True,
                            classes="input-box",
                        )
                        yield Input(
                            value="5",
                            id="words-len",
                            classes="input-box",
                            type="number",
                            validators=[Number(minimum=1)],
                            restrict="[0-9]*",
                        )
        yield CheatSheet(self.BINDINGS)

    def action_increase_len(self) -> None:
        match self.chosen_mode:
            case "symbols-pane":
                len = self.query_one("#symbols-len", expect_type=Input)
                if not len.is_valid:
                    len.value = str(16)
                    return
                len.value = str(int(len.value) + 1)
            case "words-pane":
                len = self.query_one("#words-len", expect_type=Input)
                if not len.is_valid:
                    len.value = str(5)
                    return
                len.value = str(int(len.value) + 1)
        self.action_regenerate_password()

    def action_decrease_len(self) -> None:
        match self.chosen_mode:
            case "symbols-pane":
                len = self.query_one("#symbols-len", expect_type=Input)
                if not len.is_valid:
                    len.value = str(16)
                    return
                len.value = str(max(1, int(len.value) - 1))
            case "words-pane":
                len = self.query_one("#words-len", expect_type=Input)
                if not len.is_valid:
                    len.value = str(5)
                    return
                len.value = str(max(1, int(len.value) - 1))
        self.action_regenerate_password()

    @on(Checkbox.Changed)
    def update_alphabet(self) -> None:
        upper = self.query_one("#upper", expect_type=Checkbox).value
        lower = self.query_one("#lower", expect_type=Checkbox).value
        nums = self.query_one("#nums", expect_type=Checkbox).value
        punctuation = self.query_one("#punctuation", expect_type=Checkbox).value

        new_alphabet = ""
        if upper:
            new_alphabet += string.ascii_uppercase
        if lower:
            new_alphabet += string.ascii_lowercase
        if nums:
            new_alphabet += string.digits
        if punctuation:
            new_alphabet += string.punctuation

        if new_alphabet == "":
            new_alphabet = string.ascii_lowercase

        self.alphabet = new_alphabet
        self.action_regenerate_password()

    def action_reveal_password(self) -> None:
        self.passfield.password = not self.passfield.password

    @on(Input.Submitted, "#words-len,#symbols-len")
    @on(Input.Changed, "#seps")
    @on(TabbedContent.TabActivated)
    def action_regenerate_password(self) -> None:
        choice = self.chosen_mode
        match choice:
            case "symbols-pane":
                len = self.query_one("#symbols-len", expect_type=Input)
                if not len.is_valid:
                    return
                len = int(len.value)

                self.passfield.value = passutils.get_rand_password(self.alphabet, len)
            case "words-pane":
                len = self.query_one("#words-len", expect_type=Input)
                if not len.is_valid:
                    return

                len = int(len.value)
                separators = self.query_one("#seps", expect_type=Input).value
                self.passfield.value = passutils.get_rand_passphrase(len, separators)

    def action_leave(self):
        self.app.pop_screen()

    @on(Input.Submitted, "#profile-category,#username,#url,#password")
    async def action_leave_and_save(self):
        prof_cat = self.query_one("#profile-category", expect_type=Input).value
        username = self.query_one("#username", expect_type=Input).value

        url = self.query_one("#url", expect_type=Input)
        # ensure that the validator is run even if the user made no input
        url.validate(url.value)

        if not url.is_valid:
            self.notify(
                "The URL field cannot be empty",
                title="Insertion failed",
                severity="error",
            )
            return
        url = url.value

        password = self.query_one("#password", expect_type=Input)
        password.validate(password.value)

        if not password.is_valid:
            self.notify(
                "The password field cannot be empty",
                title="Insertion failed",
                severity="error",
            )
            return
        password = password.value

        self.table.insert(prof_cat, url, username, password)
        self.app.pop_screen()


class MoveDialog(ModalScreen[Tuple[bool, bool | None, str | None]]):
    BINDINGS = [
        Binding("escape", "leave", "Leave without saving", key_display="<esc>"),
        Binding("enter", "leave_and_move", "Move", priority=True, key_display="<cr>"),
        Binding("tab", "focus_next", "Next"),
        Binding("shift+tab", "focus_previous", "Previous"),
    ]

    rows: list[str]

    def __init__(
        self,
        rows: Iterable[PassRow],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.rows = [str(row) for row in rows]
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield VerticalScroll(
                *[Static(row) for row in self.rows],
                id="entry-list",
            )
            yield Input(placeholder="destination", id="input")
            yield Checkbox("Keep categories?", id="checkbox")

        yield CheatSheet(self.BINDINGS)

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = "Move"
        input_field = self.query_one(Input)
        input_field.focus()
        vs = self.query_one(VerticalScroll)
        vs.can_focus = False

        self.watch(vs, "show_vertical_scrollbar", self.on_scrollbar)

    def on_scrollbar(self, old_val: bool, new_val: bool) -> None:
        if new_val:
            vs = self.query_one(VerticalScroll)
            vs.can_focus = True

    def action_leave(self):
        self.dismiss((False, None, None))

    def action_leave_and_move(self):
        keep_categories = self.query_one(Checkbox).value
        dst = self.query_one(Input).value
        self.dismiss((True, keep_categories, dst))


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
    table: PassTable
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


class PassTable(DataTable):
    BINDINGS = [
        Binding("shift+up", "select_up", "Select many entries"),
        Binding("shift+down", "select_down", "Select many entries"),
        Binding("ctrl+up", "deselect_up", "Select many entries"),
        Binding("ctrl+down", "deselect_down", "Select many entries"),
        Binding("escape", "deselect_all", "Remove selection"),
        Binding("space", "select_entry", "Select/deselect"),
        Binding("a", "select_all", "Select all entries"),
        Binding("d", "delete_entry", "Delete"),
        Binding("e", "edit_entry", "Delete"),
        Binding("n", "new_entry", "Add new entry"),
        Binding("m", "move_entry", "Move entry"),
        Binding("r", "reverse_selection", "Reverse selection"),
        Binding("p", "copy_password", "Copy password"),
        Binding("u", "copy_username", "Copy username"),
        Binding("f,/", "find", "Find a password"),
    ]

    def sort_sync_enumerate(self) -> None:
        self.sort(key=lambda row: (row[1], row[2], row[3]))
        self.sync()
        self.update_enumeration()

    def on_mount(self) -> None:
        self.border_title = Text.from_markup("[b][N]ew | [D]elete | [E]dit[/]")
        self.border_subtitle = Text.from_markup("[b][M]ove | [F]ind")
        self.add_column("", key="checkbox")
        self.add_column("Profile", key="Profile")
        self.add_column("Category", key="Category")
        self.add_column("URL", key="URL")
        self.cursor_type = "row"

        self.sort_sync_enumerate()
        self.set_interval(5, self.sort_sync_enumerate)


    def action_copy_password(self) -> None:
        if self.row_count > 0:
            return_code = passutils.passcli_copy(self.current_row.pass_tuple, 1)

            self.app.clear_notifications()

            if return_code != 0:
                self.notify("Ensure the password field exists.", title="Copy failed!")
            else:
                self.notify(
                    f"Password will be cleared in {passutils.get_password_clear_time()} seconds.",
                    title="Password copied!",
                )

    def action_copy_username(self) -> None:
        if self.row_count > 0:
            return_code = passutils.passcli_copy(self.current_row.pass_tuple, 2)

            self.app.clear_notifications()

            if return_code != 0:
                self.notify(
                    "Ensure the user field exists.",
                    title="Copy failed!",
                    severity="error",
                )
            else:
                self.notify(
                    f"Username will be cleared in {passutils.get_password_clear_time()} seconds.",
                    title="Password copied!",
                )

    @work
    async def action_move_entry(self) -> None:
        move, keep_cats, dst = await self.app.push_screen_wait(MoveDialog(self.selected_rows))
        if not move:
            return
        self.move(dst, keep_cats)
        # self.app.push_screen(MoveDialog(self))

    def action_new_entry(self) -> None:
        self.app.push_screen(NewEntryDialog(self))

    @work
    async def action_find(self) -> None:
        path = await self.app.push_screen_wait(FindScreen(self.all_rows))
        self.select(path)

    @work
    async def action_delete_entry(self) -> None:
        if self.row_count > 0:
            if await self.app.push_screen_wait(DeleteDialog(self.selected_rows)):
                self.delete_selected()

    def action_edit_entry(self) -> None:
        if self.row_count > 0:
            with self.app.suspend():
                passutils.passcli_edit(self.current_row.pass_tuple)

    def action_deselect_all(self) -> None:
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
        if self.row_count > 0:
            self.current_row.select()
            super().action_cursor_up()
            self.current_row.select()

            self.force_refresh()

    def action_select_down(self) -> None:
        if self.row_count > 0:
            self.current_row.select()
            super().action_cursor_down()
            self.current_row.select()

            self.force_refresh()

    def action_deselect_up(self) -> None:
        if self.row_count > 0:
            self.current_row.deselect()
            super().action_cursor_up()
            self.current_row.deselect()

            self.force_refresh()

    def action_deselect_down(self) -> None:
        if self.row_count > 0:
            self.current_row.deselect()
            super().action_cursor_down()
            self.current_row.deselect()

            self.force_refresh()

    def action_select_entry(self) -> None:
        if self.row_count > 0:
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

    def insert(self, prof_cat: str, url: str, username: str, password: str):
        pass_tuple = PassTuple.from_str(os.path.join(prof_cat, url))

        if passutils.passcli_insert(pass_tuple, username, password):
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

        self.sort_sync_enumerate()

    @property
    def current_row(self) -> PassRow:
        key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        return PassRow(key=key, table=self)

    @property
    def all_rows(self) -> Iterator[PassRow]:
        # return map(lambda row: PassRow(table=self, key=row.key), self.ordered_rows)
        for row in self.ordered_rows:
            yield PassRow(table=self, key=row.key)

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
