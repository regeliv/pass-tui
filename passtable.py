from __future__ import annotations
from rich.text import Text, TextType

from textual import on, widgets
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical, VerticalScroll, Grid
from textual.validation import Length, Number
from textual.widgets import (
    Button,
    ContentSwitcher,
    Input,
    DataTable,
    RadioButton,
    RadioSet,
    Static,
    Label,
    TabbedContent,
)
from textual.widgets.data_table import CellType, RowKey

from typing import Iterator, Tuple
from dataclasses import dataclass
import os
import string

import passutils


class DeleteDialog(ModalScreen):
    DEFAULT_CSS = """
    DeleteDialog {
        align: center middle;
    }
    #question {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #confirm {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #warning {
        color: $error;
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 20; 
        border: thick $background 80%;
        background: $surface;
    }
    #entry-list {
        column-span: 2;
        height: 5fr;
        width: 1fr;
        background: $panel
    }
    """

    BINDINGS = [
        ("escape,q", "leave", "Leave and don't delete"),
        ("enter", "delete", "Delete selected entries"),
    ]

    table: PassTable

    def __init__(
        self,
        table: PassTable,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.table = table
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:

        yield Vertical(
            Label("Are you sure you want to delete the following?", id="question"),
            VerticalScroll(
                *[Static(str(row)) for row in self.table.selected_rows],
                id="entry-list",
            ),
            Static("THIS ACTION IS IRREVERSIBLE!", id="warning"),
            Static("<enter> to confirm, <esc> to exit", id="confirm"),
            id="dialog",
        )

    def action_leave(self):
        self.app.pop_screen()

    def action_delete(self):
        self.table.delete_selected()
        self.app.pop_screen()


class NewEntryDialog(ModalScreen):
    DEFAULT_CSS = """
    NewEntryDialog {
        align: center middle;
    }
    #question {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #confirm {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #warning {
        color: $error;
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 30; 
        border: thick $background 80%;
        background: $surface;
    }
    #password-input {
        column-span: 2;
        height: 5fr;
        width: 1fr;
    }
    #radio-choice {
        width: 1fr;
    }
    #symbols {
        width: 1fr;
        grid-size: 2 3;
    }
    
    """
    BINDINGS = [
        ("escape", "leave", "Leave and don't delete"),
        ("enter", "leave_and_save", "Delete selected entries"),
        ("down,ctrl+down", "focus_next", "Focus name"),
        ("up,ctrl+up", "focus_previous", "Focus text area"),
        ("ctrl+s", "reveal_password", "Show/hide password"),
        ("ctrl+r", "regenerate_password", "Regenerate password"),
    ]

    table: PassTable
    alphabet: str

    # TODO: add entropy calculation, it shouldn't be done by the generating
    # function, but by this class
    # iterate through whole password and find out which symbol classes are used

    # TODO: add +, - keybinds

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

    @on(widgets.Checkbox.Changed)
    def update_alphabet(self) -> None:
        upper = self.query_one("#upper", expect_type=widgets.Checkbox).value
        lower = self.query_one("#lower", expect_type=widgets.Checkbox).value
        nums = self.query_one("#nums", expect_type=widgets.Checkbox).value
        punctuation = self.query_one("#punctuation", expect_type=widgets.Checkbox).value

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

    def on_mount(self) -> None:
        self.update_alphabet()

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("New", id="question")

            yield Input(placeholder="profile/category", id="profile-category")
            yield Input(placeholder="URL", id="url", validators=[Length(minimum=1)])
            yield Input(placeholder="username", id="username")

            with Vertical(id="password-input"):
                yield Input(
                    id="password",
                    password=True,
                    validators=[
                        Length(minimum=1),
                    ],
                )
                with TabbedContent("Symbols", "Words"):
                    with Grid(id="symbols"):
                        # TODO: Rename local checkbox
                        yield Input(
                            value="16",
                            id="symbols-len",
                            type="number",
                            validators=[Number(minimum=1)],
                            restrict="[0-9]*",
                        )
                        yield widgets.Checkbox("A-Z", id="upper", value=True)
                        yield widgets.Checkbox("a-z", id="lower", value=True)
                        yield widgets.Checkbox("0-9", id="nums", value=True)
                        yield widgets.Checkbox("/*+&...", id="punctuation", value=True)

                    with Grid(id="words"):
                        yield Input(
                            placeholder="seperators", id="seps", valid_empty=True
                        )
                        yield Input(
                            value="5",
                            id="words-len",
                            type="number",
                            validators=[Number(minimum=1)],
                            restrict="[0-9]*",
                        )

    @on(Input.Submitted, "#words-len,#symbols-len")
    @on(Input.Changed, "#seps")
    @on(TabbedContent.TabActivated)
    def action_regenerate_password(self) -> None:
        choice = self.chosen_mode
        match choice:
            case "tab-1":
                len = self.query_one("#symbols-len", expect_type=Input)
                if not len.is_valid:
                    return
                len = int(len.value)

                self.passfield.value = passutils.get_rand_password(self.alphabet, len)[
                    0
                ]
            case "tab-2":
                len = self.query_one("#words-len", expect_type=Input)
                if not len.is_valid:
                    return

                len = int(len.value)
                separators = self.query_one("#seps", expect_type=Input).value
                self.passfield.value = passutils.get_rand_passphrase(len, separators)[0]

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


class MoveDialog(ModalScreen):
    DEFAULT_CSS = """
        MoveDialog {
            align: center middle;
        }
        #question {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: center middle;
        }
        #confirm {
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: center middle;
        }
        #warning {
            color: $error;
            column-span: 2;
            height: 1fr;
            width: 1fr;
            content-align: center middle;
        }
        #dialog {
            grid-size: 2;
            grid-gutter: 1 2;
            grid-rows: 1fr 3;
            padding: 0 1;
            width: 60;
            height: 20; 
            border: thick $background 80%;
            background: $surface;
        }
        #entry-list {
            column-span: 2;
            height: 5fr;
            width: 1fr;
            background: $panel
        }
        """

    BINDINGS = [
        ("escape", "leave", "Leave and don't delete"),
        ("enter", "leave_and_save", "Delete selected entries"),
        ("ctrl+down,down", "focus_next", "Focus name"),
        ("ctrl+up", "focus_previous", "Focus text area"),
    ]

    table: PassTable

    def __init__(
        self,
        table: PassTable,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.table = table
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Move", id="question"),
            VerticalScroll(
                *[Static(str(row)) for row in self.table.selected_rows],
                id="entry-list",
            ),
            Input(placeholder="destination"),
            widgets.Checkbox("Keep categories?", id="checkbox"),
            Static("<enter> to confirm, <esc> to exit", id="confirm"),
            id="dialog",
        )

    def on_mount(self) -> None:
        input_field = self.query_one(Input)
        input_field.focus()

    def action_leave(self):
        self.app.pop_screen()

    def action_leave_and_save(self):
        keep_categories = self.query_one(widgets.Checkbox).value
        dst = self.query_one(Input).value
        self.table.move(dst, keep_categories)
        self.app.pop_screen()


@dataclass
class Checkbox:
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
    def checkbox(self) -> Checkbox:
        return self._data[0]

    @property
    def is_selected(self) -> bool:
        return self.checkbox.checked

    @property
    def pass_tuple(self) -> Tuple[str, str, str]:
        """Returns the tuple containing password metadata"""
        return tuple(self._data[1:])

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

    def update(self, pass_tuple: Tuple[str, str, str]) -> None:
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
    DEFAULT_CSS = """
        PassTable {
            scrollbar-background: $surface;
            scrollbar-background-hover: $surface;
            scrollbar-background-active: $surface;
            scrollbar-color: $surface;
            scrollbar-color-active: $surface;
            scrollbar-color-hover: $surface;
            scrollbar-corner-color: $surface;
            height: 100%;
        }
        PassTable > .datatable--cursor {
            background: $surface;
            color: #d75fd7; /* ansi 256-bit orchid */
        }

        PassTable > .datatable--hover {
            background: $surface;
        }

        PassTable > .datatable--header {
            background: $surface;
        }

        PassTable > .datatable--header-cursor {
            background: $surface;
            color: #d75fd7; /* ansi 256-bit orchid */
        }

        PassTable > .datatable--header-hover {
            background: $surface;
        }
    """

    BINDINGS = [
        ("shift+up", "select_up", "Select many entries"),
        ("shift+down", "select_down", "Select many entries"),
        ("ctrl+up", "deselect_up", "Select many entries"),
        ("ctrl+down", "deselect_down", "Select many entries"),
        ("escape", "deselect_all", "Remove selection"),
        ("space", "select_entry", "Select/deselect"),
        ("a", "select_all", "Select all entries"),
        ("d", "delete_entry", "Delete"),
        ("e", "edit_entry", "Delete"),
        ("n", "new_entry", "Add new entry"),
        ("m", "move_entry", "Move entry"),
        ("r", "reverse_selection", "Reverse selection"),
        ("p", "copy_password", "Copy password"),
        ("u", "copy_username", "Copy username"),
        ("t", "testing", ""),
    ]

    def sort_sync_enumerate(self) -> None:
        self.sort(key=lambda row: (row[1], row[2], row[3]))
        self.sync()
        self.update_enumeration()

    def on_mount(self) -> None:
        self.add_column("", key="checkbox")
        self.add_column("Profile", key="Profile")
        self.add_column("Category", key="Category")
        self.add_column("URL", key="URL")
        self.cursor_type = "row"

        self.sort_sync_enumerate()

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

    def action_move_entry(self) -> None:
        self.app.push_screen(MoveDialog(self))

    def action_new_entry(self) -> None:
        self.app.push_screen(NewEntryDialog(self))

    def action_delete_entry(self) -> None:
        if self.row_count > 0:
            self.app.push_screen(DeleteDialog(self))

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
        # we cannot use the iterator in the for loop directly, because the size changes
        # TODO: make it do actually delete files
        selected_rows = list(self.selected_rows)
        n_fails = 0
        for row in selected_rows:
            n_fails += not passutils.rm(row.pass_tuple)
            # self.remove_row(row.key)
        if n_fails > 0:
            self.notify(
                f"Failed to remove {n_fails} passwords.",
                title="Removal failure",
                severity="warning",
            )
        else:
            self.notify("Removal succeeded.", title="Success!")

        self.sort_sync_enumerate()
        # self.update_enumeration()

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
                synced_passes.append((Checkbox(), *new_tuple))
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
            synced_passes.append((Checkbox(), *new_passes[i]))
            i += 1

        self.clear()
        for row in synced_passes:
            self.add_row(*row)

        self.move_cursor(row=old_cursor + cursor_diff)

    def insert(self, prof_cat: str, url: str, username: str, password: str):
        pass_tuple = passutils.path_to_tuple(os.path.join(prof_cat, url))

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
                    row.update(passutils.path_to_tuple(os.path.join(dst, cats, url)))
        else:
            for row in change_list_rows:
                _, cats, url = row.pass_tuple
                ok = passutils.move(row.pass_tuple, dst)
                n_fails += not ok
                if ok:
                    row.update(passutils.path_to_tuple(os.path.join(dst, url)))

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
    def selected_tuples(self) -> Iterator[Tuple[str, str, str]]:
        count = 0
        for row in self.all_rows:
            if row.is_selected:
                count += 1
                yield row.pass_tuple

        if count == 0:
            yield self.current_row.pass_tuple
