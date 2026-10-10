"""M17.6X bounded local Ed25519 enrollment-attestor keyfile intake."""
from __future__ import annotations

import os
import stat
from typing import Final

from .auth_enrollment_attestor_ed25519_v1 import (
    REFERENCE_AUTH_ENROLLMENT_ED25519_PRIVATE_KEY_BYTES,
    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_KEYFILE_V1"
)
AUTH_ENROLLMENT_ED25519_KEY_FILENAME: Final = (
    "authentication-enrollment-ed25519.key"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment Ed25519 keyfile unavailable"
)
_REPARSE_POINT: Final = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError(
    RuntimeError
):
    """Stable fail-closed local private-key intake error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError() from None


def _is_reparse(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & _REPARSE_POINT)


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        getattr(info, "st_nlink", 0),
        getattr(info, "st_file_attributes", 0),
    )


def _same_path_handle_identity(
    path_identity: tuple[int, ...],
    handle_identity: tuple[int, ...],
) -> bool:
    if os.name != "nt":
        return path_identity == handle_identity
    return (
        path_identity[:5] + path_identity[6:]
        == handle_identity[:5] + handle_identity[6:]
    )


def _canonical_directory(directory: object) -> tuple[str, tuple[int, ...]]:
    if type(directory) is not str or not directory or "\x00" in directory:
        _fail()
    if not os.path.isabs(directory) or os.path.normpath(directory) != directory:
        _fail()
    if os.name == "nt" and directory.startswith(("\\\\", "//")):
        _fail()
    try:
        real = os.path.realpath(directory, strict=True)
        info = os.lstat(directory)
    except (OSError, ValueError, TypeError):
        _fail()
    if os.path.normcase(real) != os.path.normcase(directory):
        _fail()
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        _fail()
    if _is_reparse(info):
        _fail()
    return directory, _identity(info)


def _key_path(directory: str) -> tuple[str, tuple[int, ...]]:
    path = os.path.join(directory, AUTH_ENROLLMENT_ED25519_KEY_FILENAME)
    if os.path.dirname(path) != directory:
        _fail()
    try:
        real = os.path.realpath(path, strict=True)
        if os.path.commonpath((directory, real)) != directory:
            _fail()
        info = os.lstat(path)
    except (OSError, ValueError, TypeError):
        _fail()
    if os.path.normcase(real) != os.path.normcase(path):
        _fail()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        _fail()
    if _is_reparse(info):
        _fail()
    return path, _identity(info)


def _read_exact_private_key(
    path: str,
    expected: tuple[int, ...],
) -> bytes:
    maximum = REFERENCE_AUTH_ENROLLMENT_ED25519_PRIVATE_KEY_BYTES
    try:
        with open(path, "rb") as handle:
            opened = _identity(os.fstat(handle.fileno()))
            if not _same_path_handle_identity(expected, opened):
                _fail()
            raw = handle.read(maximum + 1)
            after_read = _identity(os.fstat(handle.fileno()))
        after_path = _identity(os.lstat(path))
        real_after = os.path.realpath(path, strict=True)
    except MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError:
        raise
    except Exception:
        _fail()

    if after_read != opened or after_path != expected:
        _fail()
    if os.path.normcase(real_after) != os.path.normcase(path):
        _fail()
    if type(raw) is not bytes or len(raw) != maximum:
        _fail()
    return raw


def load_reference_authentication_enrollment_ed25519_attestor(
    *,
    directory: str,
) -> MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor:
    """Load one exact fixed local keyfile and return only the reviewed T attestor."""

    directory, directory_identity = _canonical_directory(directory)
    try:
        key_path, key_identity = _key_path(directory)
        private_key_bytes = _read_exact_private_key(key_path, key_identity)
        directory_after = os.lstat(directory)
        if _identity(directory_after) != directory_identity:
            _fail()
        real_directory = os.path.realpath(directory, strict=True)
        if os.path.normcase(real_directory) != os.path.normcase(directory):
            _fail()
        attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
            private_key_bytes=private_key_bytes,
        )
        if type(attestor) is not MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor:
            _fail()
        return attestor
    except MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError:
        raise
    except Exception:
        _fail()


__all__ = [
    "AUTH_ENROLLMENT_ED25519_KEY_FILENAME",
    "MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError",
    "PROFILE_NAME",
    "load_reference_authentication_enrollment_ed25519_attestor",
]
