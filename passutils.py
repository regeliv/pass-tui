from __future__ import annotations
import os
import secrets
import shutil
import subprocess
from functools import cache
from typing import Iterable, NamedTuple


class PassTuple(NamedTuple):
    """A representation of a relative password path
    as used by pass

    Attributes:
        profile: first directory if any in password path, empty string otherwise
        cats: categories between first directory and the file if any, empty string otherwise
        url: the file in password path
    """

    profile: str
    cats: str
    url: str

    def __str__(self):
        return os.path.join(self.profile, self.cats, self.url)

    @property
    def fs_path(self):
        """Absolute filesystem path to the file corresponding
        to the relative pass path, includes the .gpg extension
        """
        return os.path.join(
            get_passstore_path(), self.profile, self.cats, self.url + ".gpg"
        )

    @classmethod
    def from_str(cls, path: str) -> PassTuple:
        """Converts path in string form to PassTuple

        Args:
            path: relative path to a password, as used by pass
            e.g dir1/dir2/dir3/password.org

        Returns:
            A PassTuple

        """
        split_path = path.split("/")
        match len(split_path):
            case 1:  # only url
                return cls("", "", split_path[0])
            case 2:  # profile and url
                return cls(split_path[0], "", split_path[1])
            case _:  # profile, one or more categories, url
                return cls(
                    split_path[0], os.path.join(*split_path[1:-1]), split_path[-1]
                )


def get_password_clear_time() -> str:
    """Returns how long a password is stored in clipboard

    Returns:
        A string corresponding to the number of seconds the password
        is stored in clipboard
    """
    return os.environ.get("PASSWORD_STORE_CLIP_TIME", "45")


@cache
def get_passstore_path() -> str:
    """Gets pass store path.

    Returns:
        A string corresponding to the absolute path
        of the user's password store
    """
    pass_dir = os.getenv(
        "PASSWORD_STORE_DIR",
        default=os.path.expanduser("~/.password-store"),
    )
    return pass_dir


def passstore_exists() -> bool:
    """Checks for existence of the user's password store

    Returns:
        A bool specifying whether the user's passwords store
        path exists and is a directory
    """
    return os.path.isdir(get_passstore_path())


def is_hidden(path: str) -> bool:
    """Checks if a file or directory is hidden.

    Args:
        path: Path to a directory or file, does not need actually exist

    Returns:
        A bool specifying if the directory or file is hidden
    """
    return os.path.basename(path).startswith(".")


def get_passwords() -> list[str]:
    """Fetches the list of relative password paths

    Hidden files or files in hidden directories are
    not included.

    Returns:
        A list of strings corresponding to relative password
        paths. The strings are in format used by pass executable
        to conduct operations. For example, password at
        $PASSWORD_STORE_DIR/dir1/dir2/dir3/pass.org.gpg
        has relative path of dir1/dir2/dir3/pass.org

    """
    pass_dir = get_passstore_path()
    passes = []

    for root_dir, dirs, files in os.walk(pass_dir):
        # stop os.walk from going down the hidden directory tree
        dirs = [dir for dir in dirs if not is_hidden(dir)]
        # filter what we caught in the the base path
        if not is_hidden(root_dir):
            for file in filter(lambda f: not is_hidden(f), files):
                base_path, ext = os.path.splitext(file)

                if ext == ".gpg":
                    passes.append(
                        # add one to delete the following slash
                        os.path.join(root_dir[len(pass_dir) + 1 :], base_path)
                    )

    return passes


def categorize_passwords(passwords: list[str]) -> list[PassTuple]:
    """Converts a list of paths in string form to pass tuples

    Args:
        passwords: A list of relative password paths

    Returns:
        A list of PassTuples
    """
    pass_tuples = []
    for password_path in passwords:
        pass_tuples.append(PassTuple.from_str(password_path))

    return pass_tuples


def get_categorized_passwords() -> list[PassTuple]:
    """Get a list PassTuples.

    Returns:
        A list of PassTuples
    """
    return sorted(categorize_passwords(get_passwords()))


def rand_password(alphabet: str, n: int) -> str:
    """Generate a randomv password

    Args:
        alphabet: the alphabet of characters to
        generate the password pass.
        n:

    Returns:

    """
    # I quite dislike this, because there will be most likely
    # be plenty of copies left in memory
    password = "".join([secrets.choice(alphabet) for _ in range(n)])
    return password


def rand_passphrase(n: int, separators: str) -> str:
    """Generate random passphrase, optionally with
    separators in between words.

    Args:
        n: number of words in passphrase
        separators: a string of separators, between
        each word will be a character randomly chosen
        from this string. Can be empty to disable
        separators.

    Returns:
        A random passphrase with seperators in between.
    """
    # I quite dislike this, because there will be most likely
    # be plenty of copies left in memory
    passphrase = ""
    with open("dictionaries/eff_large.wordlist", "r") as word_list:
        words = word_list.readlines()

        if len(separators) > 0:
            passphrase += secrets.choice(words).rstrip("\r\n")
            for _ in range(n - 1):
                passphrase += secrets.choice(separators) + secrets.choice(words).rstrip(
                    "\r\n"
                )
        else:
            passphrase = "".join(
                [secrets.choice(words).rstrip("\r\n") for _ in range(n)]
            )

    return passphrase


@cache
def dst_to_fs_path(dst: str) -> str:
    """Convert relative path of a directory to filesystem

    Args:
        dst: relative path to a directory in pass store

    Returns:
        the filesystem path of the directory
    """
    return os.path.join(get_passstore_path(), dst)


def move_has_conflicts(
    pass_tuples: Iterable[PassTuple], dst: str, keep_cats: bool
) -> bool:
    """Check if move have conflicts.

    Args:
        pass_tuples: An iterable of PassTuples that
        would be mobved
        dst: the destination directory of passworda
        keep_cats: whether the categories are to be preserved
        during the move

    Returns:
        True if the no conflicts would occur, False
        if they would i.e there exists a file at that path
        or any directory that is in the dst path is
        actually a file

    """
    path = os.path.join(get_passstore_path(), dst)

    if not os.path.exists(path):
        return False

    if keep_cats:
        for profile, cats, url in pass_tuples:
            url_path = os.path.join(path, profile, cats, url + ".gpg")
            if os.path.exists(url_path):
                return True
        return False

    for profile, cats, url in pass_tuples:
        url_path = os.path.join(path, url + ".gpg")
        if os.path.exists(url_path):
            return True

    return False


def move(pass_tuple: PassTuple, dst: str) -> bool:
    """Move a password

    Args:
        pass_tuple: a PassTuple of the password
        dst: new relative directory path, can be empty
        to place a password in root

    Returns:
        True if move succeeded, False if it failed.
    """
    try:
        os.makedirs(dst_to_fs_path(dst), exist_ok=True)
    except:
        return False

    try:
        shutil.move(pass_tuple.fs_path, dst_to_fs_path(dst))
    except:
        return False
    return True


def rm(pass_tuple: PassTuple) -> bool:
    """Removes a password from pass store.

    Args:
        pass_tuple: A tuple corresponding to a password

    Returns:
        True if removal succedeed, False if it failed
    """
    try:
        os.remove(pass_tuple.fs_path)
        return True
    except:
        return False


def prune() -> None:
    """Prune directories that are empty.
    Useful after moves and deletes.
    """
    for root, dirs, files in os.walk(get_passstore_path(), topdown=False):
        if not is_hidden(root) and os.path.isdir(root) and not os.listdir(root):
            print(root)
            try:
                os.rmdir(root)
            except:
                pass


def rename(pass_tuple: PassTuple, new_name: str) -> bool:
    """Renames a password.

    Args:
        pass_tuple: a PassTuple corresponding to the
        password to rename

        new_name: a new name for the password

    Returns:
        True if rename operation succeeded, False if it failed
    """
    try:
        old_path = pass_tuple.fs_path
        new_path = os.path.join(pass_tuple.profile, pass_tuple.cats, new_name + ".gpg")
        new_path = dst_to_fs_path(new_path)
        os.renames(old_path, new_path)
        return True
    except:
        return False


def passcli_copy(pass_tuple: PassTuple, n: int) -> bool:
    """Copy a password or other line to clipboard.

    Args:
        pass_tuple: a PassTuple of the password to copy.
        n: the line to copy, 1 for password, 2 for username

    Returns:
        True if operation copy succeeded, False if it failed
    """
    p = subprocess.run(
        ["pass", "show", f"-c{n}", str(pass_tuple)],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return p.returncode == 0


def passcli_edit(pass_tuple: PassTuple) -> None:
    """Launches the user's editor to edit the password.

    Args:
        pass_tuple: a PassTuple of the password.
    """
    subprocess.run(["pass", "edit", str(pass_tuple)])


def passcli_insert(pass_tuple: PassTuple, username: str, password: str) -> bool:
    """Creates pas

    Args:
        pass_tuple: a PassTuple of the password
        username: a string to be inserted as the second field
        password: a string to be inserted as the first field

    Returns:
        True if insertion succeeded, False if it failed.
    """
    target_path = pass_tuple.fs_path
    if os.path.exists(target_path):
        return False

    p = subprocess.Popen(
        ["pass", "insert", "--multiline", str(pass_tuple)],
        env=os.environ,
        stdout=subprocess.DEVNULL,
        stdin=subprocess.PIPE,
    )
    if username:
        p.communicate(bytes(password + "\n" + username + "\n", "utf-8"))
    else:
        p.communicate(bytes(password + "\n", "utf-8"))

    if p.stdin:
        p.stdin.close()

    return p.returncode == 0
