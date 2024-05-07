from functools import cached_property
import string
from typing import Iterable, NamedTuple, Tuple
import rapidfuzz
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.validation import Length, Number, ValidationResult, Validator
from textual.widgets import Checkbox, Input, OptionList, Static, TabPane, TabbedContent
from cheatsheet import CheatSheet
from passrow import PassRow
from passutils import PassTuple
import passutils
import os


class ValidFilePath(Validator):

    def validate(self, value: str) -> ValidationResult:
        if value.startswith("/") or value.endswith("/"):
            return self.failure("Path cannot start or end with a /")
        else:
            return self.success()


class ValidDirPath(Validator):

    def validate(self, value: str) -> ValidationResult:
        if value.startswith("/"):
            return self.failure("Path cannot start with a /")
        else:
            return self.success()


class ValidURL(Validator):
    def validate(self, value: str) -> ValidationResult:
        if "/" in value:
            return self.failure("URL cannot contain a /")
        else:
            return self.success()


class RenameDialog(ModalScreen[str | None]):
    BINDINGS = [
        Binding("escape", "exit", "Exit", priority=True, key_display="<esc>"),
        Binding(
            "enter",
            "rename_and_exit",
            "Select and exit",
            priority=True,
            key_display="<cr>",
        ),
    ]

    password: PassTuple
    prof_cat: str

    def __init__(
        self,
        password: PassTuple,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.password = password
        self.prof_cat = os.path.join(password.profile, password.cats)
        if not self.prof_cat.endswith("/") and not len(self.prof_cat) == 0:
            self.prof_cat += "/"

        super().__init__(name, id, classes)

    def on_mount(self) -> None:
        self.query_one(Vertical).border_title = "Rename"

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(str(self.password))
            yield Static(Text.from_markup("[b]⇣[/]"))
            yield Static(
                Text.from_markup(f"{self.prof_cat}[b]{self.password.url}[/]"),
                id="destination",
            )
            # TODO: add validation
            yield Input(validators=[Length(minimum=1), ValidFilePath()])
        yield CheatSheet(self.BINDINGS)

    @on(Input.Changed)
    def update_destination(self) -> None:
        dst = self.query_one("#destination", expect_type=Static)
        user_input = self.query_one(Input).value
        dst.update(f"{self.prof_cat}[b]{user_input}[/]")

    def action_exit(self) -> None:
        self.dismiss(None)

    def action_rename_and_exit(self) -> None:
        user_input = self.query_one(Input)
        if not user_input.is_valid:
            self.notify("Invalid destination.", title="Rename fail!", severity="error")
            return

        self.dismiss(self.query_one(Input).value)


class FindScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("escape", "leave", "Exit dialog"),
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
        Binding("escape", "leave", "Exit dialog", key_display="<esc>"),
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


class NewEntryTuple(NamedTuple):
    create: bool
    prof_cat: str = ""
    url: str = ""
    username: str = ""
    password: str = ""


class NewEntryDialog(ModalScreen[NewEntryTuple]):
    BINDINGS = [
        Binding("escape", "leave", "Exit dialog", key_display="<esc>"),
        Binding("enter", "", "Add new password", key_display="<cr>"),
        Binding("tab", "focus_next", "Next", key_display="<tab>"),
        Binding("shift+tab", "focus_previous", "Previous", key_display="shift+<tab>"),
        Binding(
            "ctrl+s", "reveal_password", "Show/hide password", key_display="ctrl+s"
        ),
        Binding(
            "ctrl+r", "regenerate_password", "Regenerate password", key_display="ctrl+r"
        ),
        Binding(
            "ctrl+a",
            "increase_len",
            "Increase password length",
            key_display="ctrl+a",
            priority=True,
        ),
        Binding(
            "ctrl+x",
            "decrease_len",
            "Decrease password length",
            key_display="ctrl+x",
            priority=True,
        ),
    ]

    alphabet: str

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
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
            yield Input(
                id="url",
                classes="input-box",
                validators=[Length(minimum=1), ValidURL()],
            )
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
        self.dismiss(NewEntryTuple(create=False))
        # self.app.pop_screen()

    @on(Input.Submitted, "#profile-category,#username,#url,#password")
    async def action_leave_and_save(self):
        prof_cat = self.query_one("#profile-category", expect_type=Input).value
        username = self.query_one("#username", expect_type=Input).value

        url = self.query_one("#url", expect_type=Input)
        # ensure that the validator is run even if the user made no input
        url.validate(url.value)

        if not url.is_valid:
            self.notify(
                "The URL cannot be empty or contain a /",
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

        # self.table.insert(prof_cat, url, username, password)
        self.dismiss(
            NewEntryTuple(
                create=True,
                prof_cat=prof_cat,
                url=url,
                username=username,
                password=password,
            )
        )


class MoveDialog(ModalScreen[Tuple[bool, bool, str]]):
    BINDINGS = [
        Binding("escape", "leave", "Exit dialog", key_display="<esc>"),
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
            yield Input(
                placeholder="destination", id="input", validators=[ValidDirPath()]
            )
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
        self.dismiss((False, False, ""))

    def action_leave_and_move(self):
        user_input = self.query_one(Input)
        if not user_input.is_valid:
            self.notify("Invalid destination.", title="Move failed!", severity="error")
            return
        dst = user_input.value
        keep_categories = self.query_one(Checkbox).value
        self.dismiss((True, keep_categories, dst))
