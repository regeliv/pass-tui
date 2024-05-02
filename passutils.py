import os
import shutil
import subprocess
from functools import cache, cmp_to_key
from typing import Tuple, Iterable


@cache
def get_passstore_path() -> str:
    pass_dir = os.getenv(
        "PASSWORD_STORE_DIR",
        default=os.path.expanduser("~/.password-store"),
    )
    return pass_dir


def passstore_exists() -> bool:
    return os.path.isdir(get_passstore_path())


def is_hidden(path: str) -> bool:
    return os.path.basename(path).startswith(".")


def get_passwords() -> list[str]:
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


def path_to_tuple(password_path: str) -> Tuple[str, str, str]:
    """Given a string of the form (profile)?/(category/)*(url)
    returns a tuple of three strings of the form:
    (profile, category1/category2/..., url).
    If no profile or category is specified the corresponding field is empty
    """
    split_path = password_path.split("/")
    match len(split_path):
        case 1:  # only url
            return ("", "", split_path[0])
        case 2:  # profile and url
            return (split_path[0], "", split_path[1])
        case _:  # profile, one or more categories, url
            return (split_path[0], os.path.join(*split_path[1:-1]), split_path[-1])


def categorize_passwords(passwords: list[str]) -> list[Tuple[str, str, str]]:
    pass_tuples = []
    for password_path in passwords:
        pass_tuples.append(path_to_tuple(password_path))

    return pass_tuples


def get_categorized_passwords() -> list[Tuple[str, str, str]]:
    return categorize_passwords(get_passwords())


@cache
def full_passpath(dst: str) -> str:
    return os.path.join(get_passstore_path(), dst)


@cache
def tuple_to_path(pass_tuple: Tuple[str, str, str]) -> str:
    return os.path.join(pass_tuple[0], *pass_tuple[1:])


def passcli_edit(pass_tuple: Tuple[str, str, str]) -> None:
    subprocess.run(["pass", "edit", tuple_to_path(pass_tuple)])


def move_has_conflicts(
    pass_tuples: Iterable[Tuple[str, str, str]], dst: str, keep_cats: bool
) -> bool:
    """Returns true if a move of the following passwords would result in a conflict
    Move will result in a conflict if the directory or file with the same name
    exists
    """
    path = os.path.join(get_passstore_path(), dst)

    if not os.path.exists(path):
        return False

    # move function will error on malicious user anyway
    # if not os.path.isdir(path):
    #     return True

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


def move(pass_tuple: Tuple[str, str, str], dst: str) -> bool:
    """Moves the file corresponding to pass_tuple to dst path in the pass store
    returns True on success, False on failure
    """
    # TODO: delete directory if it was left empty
    try:
        os.makedirs(full_passpath(dst), exist_ok=True)
    except:
        return False

    try:
        shutil.move(
            full_passpath(tuple_to_path(pass_tuple) + ".gpg"), full_passpath(dst)
        )
    except:
        return False
    return True
