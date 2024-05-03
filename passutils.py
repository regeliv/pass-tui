import math
import os
import secrets
import shutil
import subprocess
from functools import cache
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
    return sorted(categorize_passwords(get_passwords()))


def get_password_clear_time() -> str:
    return os.environ.get("PASSWORD_STORE_CLIP_TIME", "45")


def get_rand_password(alphabet: str, n: int) -> Tuple[str, float]:
    # I quite dislike this, because there will be most likely
    # be plenty of copies
    password = "".join([secrets.choice(alphabet) for _ in range(n)])
    entropy = math.log2(len(alphabet) ** n)
    return password, entropy


def get_rand_passphrase(n: int, separators: str) -> Tuple[str, float]:
    # I quite dislike this, because there will be most likely
    # be plenty of copies
    passphrase = ""
    with open("eff_large.wordlist", "r") as word_list:
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

    entropy = 7776**n
    if len(separators) > 0:
        print(f"{len(separators)} {n - 1}")
        entropy *= len(separators) ** (n - 1)

    entropy = math.log2(entropy)

    return (passphrase, entropy)


def passcli_copy(pass_tuple: Tuple[str, str, str], n: int) -> int:
    # passing env to ensure local shell vars are passed
    # popen allows to easily capture stderr and stdout
    p = subprocess.run(
        ["pass", "show", f"-c{n}", tuple_to_path(pass_tuple)],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return p.returncode


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


def passcli_insert(
    pass_tuple: Tuple[str, str, str], username: str, password: str
) -> bool:
    """Creates a file corresponding to the pass_tuple
    with password as the first line and username as second
    """
    target_path = full_passpath(tuple_to_path(pass_tuple))
    if os.path.exists(target_path):
        return False

    p = subprocess.Popen(
        ["pass", "insert", "--multiline", tuple_to_path(pass_tuple)],
        env=os.environ,
        stdout=subprocess.DEVNULL,
        stdin=subprocess.PIPE,
    )
    if username:
        p.communicate(bytes(password + "\n" + username + "\n", "utf-8"))
    else:
        p.communicate(bytes(password + "\n", "utf-8"))

    # appeasing lsp
    if p.stdin:
        p.stdin.close()

    return p.returncode == 0
