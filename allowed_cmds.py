"""Shared allowlist. Remote uses this to refuse before any proxy call."""
import re

ALLOWED = frozenset(
    {
        "basename",
        "cal",
        "cat",
        "chmod",
        "cp",
        "cut",
        "date",
        "df",
        "diff",
        "dirname",
        "du",
        "echo",
        "env",
        "false",
        "file",
        "find",
        "grep",
        "head",
        "hostname",
        "id",
        "ln",
        "ls",
        "md5",
        "mkdir",
        "mv",
        "printenv",
        "printf",
        "pwd",
        "readlink",
        "realpath",
        "rm",
        "rmdir",
        "shasum",
        "sleep",
        "sort",
        "stat",
        "tail",
        "touch",
        "tr",
        "true",
        "uname",
        "uniq",
        "wc",
        "which",
        "whoami",
    }
)

SHELL_META = re.compile(r"[|><;&`$]")


def has_shell_meta(text: str) -> bool:
    return bool(SHELL_META.search(text or ""))


def is_recursive_rm(argv) -> bool:
    if not argv or argv[0] != "rm":
        return False
    for a in argv[1:]:
        if a == "--":
            break
        if a == "--recursive":
            return True
        if a.startswith("-") and not a.startswith("--") and "r" in a[1:]:
            return True
    return False
