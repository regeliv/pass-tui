import os
import subprocess
from typing import Tuple


def get_passstore_path() -> str:
    pass_dir = os.getenv("PASSWORD_STORE_DIR")
    if pass_dir is None:
        pass_dir = os.path.expanduser("~/.password-store")
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


def categorize_password(password_path: str) -> Tuple[str, str, str]:
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
        pass_tuples.append(categorize_password(password_path))

    return pass_tuples


def get_categorized_passwords() -> list[Tuple[str, str, str]]:
    return categorize_passwords(get_passwords())


def passcli_edit(pass_tuple: Tuple[str, str, str]) -> None:
    subprocess.run(["pass", "edit", os.path.join(pass_tuple[0], *pass_tuple[1:])])
