"""Kernel-enforced per-delivery sandbox for untrusted repository processes."""

from __future__ import annotations

import ctypes
from ctypes import c_int, c_long, c_uint32, c_uint64, c_void_p
import os
from pathlib import Path
import platform
import shutil
import sys
from uuid import UUID


_CREATE_RULESET = 444
_ADD_RULE = 445
_RESTRICT_SELF = 446
_CREATE_RULESET_VERSION = 1
_RULE_PATH_BENEATH = 1
_PR_SET_NO_NEW_PRIVS = 38

_FS_EXECUTE = 1 << 0
_FS_WRITE_FILE = 1 << 1
_FS_READ_FILE = 1 << 2
_FS_READ_DIR = 1 << 3
_FS_REMOVE_DIR = 1 << 4
_FS_REMOVE_FILE = 1 << 5
_FS_MAKE_CHAR = 1 << 6
_FS_MAKE_DIR = 1 << 7
_FS_MAKE_REG = 1 << 8
_FS_MAKE_SOCK = 1 << 9
_FS_MAKE_FIFO = 1 << 10
_FS_MAKE_BLOCK = 1 << 11
_FS_MAKE_SYM = 1 << 12
_FS_REFER = 1 << 13
_FS_TRUNCATE = 1 << 14
_FS_IOCTL_DEV = 1 << 15
_NET_BIND_TCP = 1 << 0
_NET_CONNECT_TCP = 1 << 1
_SCOPE_SIGNAL = 1 << 1


class LandlockUnavailable(RuntimeError):
    """Raised when the host cannot enforce the admitted sandbox contract."""


class _RulesetAttr(ctypes.Structure):
    _fields_ = [
        ("handled_access_fs", c_uint64),
        ("handled_access_net", c_uint64),
        ("scoped", c_uint64),
    ]


class _PathBeneathAttr(ctypes.Structure):
    _fields_ = [("allowed_access", c_uint64), ("parent_fd", c_int)]


def _libc():
    library = ctypes.CDLL(None, use_errno=True)
    library.syscall.restype = c_long
    library.prctl.argtypes = [c_int, c_long, c_long, c_long, c_long]
    library.prctl.restype = c_int
    return library


def landlock_abi_version() -> int:
    if platform.system() != "Linux":
        raise LandlockUnavailable("Landlock requires a Linux kernel")
    result = _libc().syscall(
        _CREATE_RULESET, c_void_p(), c_uint32(0), c_uint32(_CREATE_RULESET_VERSION)
    )
    if result < 0:
        code = ctypes.get_errno()
        raise LandlockUnavailable(f"Landlock ABI query failed with errno {code}")
    return int(result)


def _handled_fs(abi: int) -> int:
    access = (
        _FS_EXECUTE | _FS_WRITE_FILE | _FS_READ_FILE | _FS_READ_DIR
        | _FS_REMOVE_DIR | _FS_REMOVE_FILE | _FS_MAKE_CHAR | _FS_MAKE_DIR
        | _FS_MAKE_REG | _FS_MAKE_SOCK | _FS_MAKE_FIFO | _FS_MAKE_BLOCK
        | _FS_MAKE_SYM
    )
    if abi >= 2:
        access |= _FS_REFER
    if abi >= 3:
        access |= _FS_TRUNCATE
    if abi >= 5:
        access |= _FS_IOCTL_DEV
    return access


def _add_path_rule(ruleset_fd: int, path: Path, access: int) -> None:
    descriptor = os.open(path, os.O_PATH | os.O_CLOEXEC)
    try:
        rule = _PathBeneathAttr(allowed_access=access, parent_fd=descriptor)
        result = _libc().syscall(
            _ADD_RULE, c_int(ruleset_fd), c_int(_RULE_PATH_BENEATH),
            ctypes.byref(rule), c_uint32(0),
        )
        if result < 0:
            code = ctypes.get_errno()
            raise LandlockUnavailable(
                f"Landlock rejected path rule for {path} with errno {code}"
            )
    finally:
        os.close(descriptor)


def apply_landlock(workspace: Path, scratch: Path) -> int:
    """Restrict this process and descendants before executing repository code."""

    abi = landlock_abi_version()
    if abi < 6:
        raise LandlockUnavailable(
            f"Landlock ABI {abi} cannot enforce filesystem, network, and signal isolation"
        )
    handled_fs = _handled_fs(abi)
    attributes = _RulesetAttr(
        handled_access_fs=handled_fs,
        handled_access_net=_NET_BIND_TCP | _NET_CONNECT_TCP,
        scoped=_SCOPE_SIGNAL,
    )
    ruleset_fd = _libc().syscall(
        _CREATE_RULESET, ctypes.byref(attributes),
        c_uint32(ctypes.sizeof(attributes)), c_uint32(0),
    )
    if ruleset_fd < 0:
        code = ctypes.get_errno()
        raise LandlockUnavailable(f"Landlock ruleset creation failed with errno {code}")
    read_access = _FS_EXECUTE | _FS_READ_FILE | _FS_READ_DIR
    write_access = handled_fs
    try:
        for raw in ("/usr", "/opt", "/bin", "/lib", "/lib64", "/etc"):
            path = Path(raw)
            if path.exists():
                _add_path_rule(ruleset_fd, path, read_access)
        for raw in ("/dev/null", "/dev/urandom", "/dev/random"):
            path = Path(raw)
            if path.exists():
                _add_path_rule(ruleset_fd, path, _FS_READ_FILE | _FS_WRITE_FILE)
        _add_path_rule(ruleset_fd, workspace, write_access)
        _add_path_rule(ruleset_fd, scratch, write_access)
        library = _libc()
        if library.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            code = ctypes.get_errno()
            raise LandlockUnavailable(f"no_new_privs failed with errno {code}")
        if library.syscall(_RESTRICT_SELF, c_int(ruleset_fd), c_uint32(0)) != 0:
            code = ctypes.get_errno()
            raise LandlockUnavailable(f"Landlock restriction failed with errno {code}")
    finally:
        os.close(ruleset_fd)
    return abi


class LandlockProcessSandbox:
    """Prepare one fresh kernel sandbox domain for each process delivery."""

    minimum_abi = 6

    def __init__(self, scratch_root: Path | None = None) -> None:
        self.scratch_root = (scratch_root or Path("/tmp")).resolve()
        self.abi_version = landlock_abi_version()
        if self.abi_version < self.minimum_abi:
            raise LandlockUnavailable(
                f"Landlock ABI {self.abi_version} is below required ABI {self.minimum_abi}"
            )

    def command(
        self, delivery_id: UUID, workspace: Path, cwd: Path, argv: list[str]
    ) -> tuple[list[str], Path]:
        scratch = self.scratch_root / f"watt-sandbox-{delivery_id.hex}"
        scratch.mkdir(mode=0o700, parents=False, exist_ok=False)
        launcher = Path(__file__).resolve()
        return (
            [sys.executable, str(launcher), "--launch", str(workspace),
             str(cwd), str(scratch), "--", *argv],
            scratch,
        )

    @staticmethod
    def cleanup(scratch: Path) -> None:
        shutil.rmtree(scratch, ignore_errors=True)

    def readiness(self) -> dict[str, object]:
        return {
            "isolation": "landlock-per-delivery",
            "landlock_abi": self.abi_version,
            "signal_scope": True,
            "tcp_network_denied": True,
        }


def _launch(arguments: list[str]) -> None:
    if len(arguments) < 6 or arguments[0] != "--launch" or "--" not in arguments:
        raise SystemExit("invalid Landlock launcher invocation")
    separator = arguments.index("--")
    workspace = Path(arguments[1]).resolve()
    cwd = Path(arguments[2]).resolve()
    scratch = Path(arguments[3]).resolve()
    argv = arguments[separator + 1 :]
    if not argv or workspace != cwd and workspace not in cwd.parents:
        raise SystemExit("invalid sandbox workspace or command")
    apply_landlock(workspace, scratch)
    os.chdir(cwd)
    os.environ["TMPDIR"] = str(scratch)
    os.environ["TMP"] = str(scratch)
    os.environ["TEMP"] = str(scratch)
    os.execvpe(argv[0], argv, os.environ)


if __name__ == "__main__":
    _launch(sys.argv[1:])
