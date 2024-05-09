from functools import cached_property
import string
from typing import Iterable, NamedTuple, Tuple
import rapidfuzz
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen, ScreenResultType
from textual.validation import Length, Number
from textual.widgets import Checkbox, Input, OptionList, Static, TabPane, TabbedContent

from widgets.cheatsheet import CheatSheet
from widgets.passrow import PassRow
from widgets.validators import *

from passutils import PassTuple
import passutils
import os


class ModalWithCheat(ModalScreen[ScreenResultType]):
    """ModalScreen with the CheatSheet widget and
    its binding included.
    """

    BINDINGS = [
        Binding("ctrl+t", "toggle_help", "Toggle help", priority=True),
    ]

    def action_toggle_help(self):
        """Toggle cheatsheet."""
        try:
            cheatsheet = self.query_one(CheatSheet)
            cheatsheet.remove()
        except NoMatches:
            self.mount(CheatSheet(self.BINDINGS))


class VimVerticalScroll(VerticalScroll):
    """VerticalScroll with vim keybinds for moving up
    and down.
    """

    BINDINGS = [
        Binding("j", "scroll_down", "Scroll one line down"),
        Binding("k", "scroll_up", "Scroll one line up"),
    ]


class RenameDialog(ModalWithCheat[str | None]):
    """A dialog allowing user to rename one password,
    possibly moving it into a directory.

    Attributes:
        password: a PassTuple of the password being renamed.
        prof_cat: the profile and category fields of the PassTuple
        squashed into one string.
    """

    BINDINGS = ModalWithCheat.BINDINGS + [
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
            yield Input(validators=[Length(minimum=1), ValidFilePath()])
        yield CheatSheet(self.BINDINGS)

    @on(Input.Changed)
    def update_destination(self) -> None:
        """Update the string showing the result of the rename."""
        dst = self.query_one("#destination", expect_type=Static)
        user_input = self.query_one(Input).value
        dst.update(f"{self.prof_cat}[b]{user_input}[/]")

    def action_exit(self) -> None:
        """Leave dialog without making the rename."""
        self.dismiss(None)

    def action_rename_and_exit(self) -> None:
        """Leave the dialog and rename the password."""
        user_input = self.query_one(Input)
        if not user_input.is_valid:
            self.notify("Invalid destination.", title="Rename fail!", severity="error")
            return

        self.dismiss(self.query_one(Input).value)


class FindScreen(ModalScreen[str]):
    """Fuzzy finder widget for the passwords in the pass store.

    Attributes:
        rows: a list of passwords as relative path strings, that is to be searched
    """

    BINDINGS = [
        Binding("escape", "quit", "Exit dialog"),
        Binding("enter", "select_and_quit", priority=True),
        Binding("down", "down", "Move", priority=True),
        Binding("up", "up", "", priority=True),
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
        """The OptionList widget with passwords
        ranked according to the fuzzy finder algorithm.
        """
        return self.query_one(OptionList)

    def on_mount(self) -> None:
        self.option_list.add_options(self.rows)
        self.option_list.highlighted = 0
        self.option_list.can_focus = False

    def compose(self) -> ComposeResult:
        with Vertical(id="vertical"):
            yield Input(id="input")
            yield OptionList(id="option-list")

    @on(Input.Changed)
    def regenerate(self) -> None:
        """Create a new list of ranked passwords."""
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

    def action_down(self) -> None:
        """Move the cursor in the option list down."""
        # We cannot use action_scroll_up here because, we use highlight
        # not selection as the option list is not focusable

        if self.option_list.highlighted is not None:
            self.option_list.highlighted += 1

    def action_up(self) -> None:
        """Move the cursor in the option list up."""
        if self.option_list.highlighted is not None:
            self.option_list.highlighted -= 1

    def action_quit(self) -> None:
        """Leave the srceen without making a selection."""
        self.app.pop_screen()

    def action_select_and_quit(self) -> None:
        """Leave the screen and select the password to go to."""
        option_idx = self.option_list.highlighted

        if option_idx is not None:
            option = str(self.option_list.get_option_at_index(option_idx).prompt)
            self.dismiss(option)


class DeleteDialog(ModalWithCheat[bool]):
    BINDINGS = [
        Binding("escape", "quit", "Exit dialog", key_display="<esc>"),
        Binding("enter", "quit_and_delete", "Delete", key_display="<cr>"),
        Binding("up", "", "Scroll up", key_display="↑"),
        Binding("down", "", "Scroll down", key_display="↓"),
    ] + ModalWithCheat.BINDINGS

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
            yield VimVerticalScroll(
                *[Static(str(row)) for row in self.rows],
                id="entry-list",
            )
            yield Static(
                Text.from_markup("[b red]THIS ACTION IS IRREVERSIBLE![/]"), id="warning"
            )
        yield CheatSheet(self.BINDINGS)

    def action_quit(self):
        self.dismiss(False)

    def action_quit_and_delete(self):
        self.dismiss(True)


class NewEntryTuple(NamedTuple):
    """Tuple that is the result of a user quiting the
    new entry dialog.

    Attributes:
        create: whether the user chose to create a new password.
        prof_cat: profile and category fields of a PassTuple squashed
        into one string.
        url: the address of the website or, equivalently
        the file name of the password
        username: the username that the user entered
        password: the password that the user chose
    """

    create: bool
    prof_cat: str = ""
    url: str = ""
    username: str = ""
    password: str = ""


class NewEntryDialog(ModalWithCheat[NewEntryTuple]):
    """Dialog allowing the user to create a new password.

    Attributes:
        alphabet: the alphabet of characters a random
        password is generated from.
    """

    BINDINGS = [
        Binding("escape", "quit", "Exit dialog", key_display="<esc>"),
        Binding(
            "enter",
            "submit_input",
            "Add new password",
            key_display="<cr>",
            priority=True,
        ),
        Binding("tab", "focus_next", "Next", key_display="<tab>"),
        Binding("shift+tab", "focus_previous", "Previous", key_display="shift+<tab>"),
        Binding(
            "ctrl+s", "reveal_hide_password", "Show/hide password", key_display="ctrl+s"
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
        Binding("ctrl+p", "change_tab", "Change password tab"),
    ] + ModalWithCheat.BINDINGS

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
        """The Input field containing a password."""
        return self.query_one("#password", expect_type=Input)

    @property
    def chosen_mode(self) -> str:
        """A string that is either "words-pane", or "symbols-pane",
        corresponding to which password generation tab the user is in.
        """
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

    @on(Checkbox.Changed)
    def update_alphabet(self) -> None:
        """Update the alphabet of characters used to generate a password."""
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

    def action_reveal_hide_password(self) -> None:
        """Reveal or hide the password field."""
        self.passfield.password = not self.passfield.password

    def action_submit_input(self) -> None:
        """Sumbit input and either create a new entry or
        regenerate the password field."""

        if self.focused is None:
            self.action_quit_and_new()
            return

        match self.focused.id:
            case "words-len" | "symbols-len" | "seps":
                self.action_regenerate_password()
            case _:
                self.action_quit_and_new()

    def action_change_tab(self) -> None:
        """Change the password creation tab
        from symbols to words and vice versa
        """
        tc = self.query_one(TabbedContent)
        choice = self.chosen_mode
        match choice:
            case "symbols-pane":
                tc.active = "words-pane"
            case "words-pane":
                tc.active = "symbols-pane"

    @on(TabbedContent.TabActivated)
    def action_regenerate_password(self) -> None:
        """Generate a new random password or passphrase."""
        choice = self.chosen_mode
        match choice:
            case "symbols-pane":
                len = self.query_one("#symbols-len", expect_type=Input)
                if not len.is_valid:
                    return
                len = int(len.value)

                self.passfield.value = passutils.rand_password(self.alphabet, len)
            case "words-pane":
                len = self.query_one("#words-len", expect_type=Input)
                if not len.is_valid:
                    return

                len = int(len.value)
                separators = self.query_one("#seps", expect_type=Input).value
                self.passfield.value = passutils.rand_passphrase(len, separators)

    def action_quit(self):
        """Close dialog without creating a new password."""
        self.dismiss(NewEntryTuple(create=False))

    def action_quit_and_new(self):
        """Close dialog and create new password."""
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

        self.dismiss(
            NewEntryTuple(
                create=True,
                prof_cat=prof_cat,
                url=url,
                username=username,
                password=password,
            )
        )

    def action_increase_len(self) -> None:
        """Increase the length of the randomly
        generated password or passphrase."""
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
        """Decrease the length of the randomly
        generated password or passphrase."""
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


class MoveDialog(ModalWithCheat[Tuple[bool, bool, str]]):
    """Dialog that allows the user to move many passwords.

    Attributes:
        rows: rows that slated for the move.
    """

    BINDINGS = [
        Binding("escape", "quit", "Exit dialog", key_display="<esc>"),
        Binding("enter", "quit_and_move", "Move", priority=True, key_display="<cr>"),
        Binding("tab", "focus_next", "Next"),
        Binding("shift+tab", "focus_previous", "Previous"),
        Binding("up", "up", "Scroll up", key_display="↑"),
        Binding("down", "down", "Scroll down", key_display="↓"),
    ] + ModalWithCheat.BINDINGS

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
            with VimVerticalScroll(id="entry-list"):
                for row in self.rows:
                    yield Static(row)

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

    def action_up(self) -> None:
        """Move cursor in password list up."""
        vs = self.query_one(VerticalScroll)
        vs.action_scroll_up()

    def action_down(self) -> None:
        """Move cursor in password list down."""
        vs = self.query_one(VerticalScroll)
        vs.action_scroll_down()

    def action_quit(self):
        """Quit the dialog without moving the passwords."""
        self.dismiss((False, False, ""))

    def action_quit_and_move(self):
        """Quit the dialog and move the passwords."""
        user_input = self.query_one(Input)
        if not user_input.is_valid:
            self.notify("Invalid destination.", title="Move failed!", severity="error")
            return
        dst = user_input.value
        keep_categories = self.query_one(Checkbox).value
        self.dismiss((True, keep_categories, dst))
