from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from marketplace.reference.auth_enrollment_attestor_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
)
from marketplace.reference.auth_enrollment_attestor_keyfile_v1 import (
    AUTH_ENROLLMENT_ED25519_KEY_FILENAME,
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError,
    _identity,
    _read_exact_private_key,
    load_reference_authentication_enrollment_ed25519_attestor,
)


MODULE = "marketplace.reference.auth_enrollment_attestor_keyfile_v1"
PRIVATE_KEY = bytes(range(32))
ERROR_MESSAGE = "reference authentication enrollment Ed25519 keyfile unavailable"


def _write_key(directory: Path, value: bytes = PRIVATE_KEY) -> Path:
    path = directory / AUTH_ENROLLMENT_ED25519_KEY_FILENAME
    path.write_bytes(value)
    return path


def _stat_proxy(info: os.stat_result, **changes: int) -> SimpleNamespace:
    names = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_nlink",
        "st_file_attributes",
    )
    values = {name: int(getattr(info, name, 0)) for name in names}
    values.update(changes)
    return SimpleNamespace(**values)


class M176XReferenceAuthenticationEnrollmentAttestorKeyfileTests(
    unittest.TestCase
):
    def test_profile_fixed_filename_and_exact_attestor_result(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_KEYFILE_V1",
        )
        self.assertEqual(
            AUTH_ENROLLMENT_ED25519_KEY_FILENAME,
            "authentication-enrollment-ed25519.key",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_key(root)
            result = load_reference_authentication_enrollment_ed25519_attestor(
                directory=str(root)
            )

        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
        )
        self.assertFalse(hasattr(result, "private_key_bytes"))
        self.assertFalse(hasattr(result, "_private_key_bytes"))

    def test_success_uses_one_read_only_open_and_one_exact_t_construction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = _write_key(root)
            real_open = open
            calls: list[tuple[str, str]] = []

            def tracked_open(path, mode="r", *args, **kwargs):
                calls.append((os.fspath(path), mode))
                return real_open(path, mode, *args, **kwargs)

            with (
                patch("builtins.open", side_effect=tracked_open),
                patch(
                    f"{MODULE}.MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor",
                    wraps=MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
                ) as build_attestor,
            ):
                result = (
                    load_reference_authentication_enrollment_ed25519_attestor(
                        directory=str(root)
                    )
                )

        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
        )
        self.assertEqual(calls, [(str(target), "rb")])
        build_attestor.assert_called_once_with(private_key_bytes=PRIVATE_KEY)

    def test_load_does_not_attest_or_sign(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_key(root)
            with patch.object(
                MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
                "attest_authentication_enrollment",
                side_effect=AssertionError("attestation used"),
            ) as attest:
                result = (
                    load_reference_authentication_enrollment_ed25519_attestor(
                        directory=str(root)
                    )
                )

        attest.assert_not_called()
        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
        )

    def test_relative_noncanonical_and_redirected_directory_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_key(root)
            for directory in (root.name, str(root) + os.sep):
                with self.subTest(directory=directory):
                    with self.assertRaises(
                        MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
                    ):
                        load_reference_authentication_enrollment_ed25519_attestor(
                            directory=directory
                        )

            with (
                patch(
                    f"{MODULE}.os.path.realpath",
                    return_value=str(root.parent),
                ),
                self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
                ),
            ):
                load_reference_authentication_enrollment_ed25519_attestor(
                    directory=str(root)
                )

    def test_child_escape_fails_before_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = _write_key(root)
            real_realpath = os.path.realpath

            def escaped_realpath(path, *, strict=False):
                if os.fspath(path) == str(target):
                    return str(root.parent / "outside-private-key")
                return real_realpath(path, strict=strict)

            with (
                patch(f"{MODULE}.os.path.realpath", side_effect=escaped_realpath),
                patch("builtins.open") as opened,
                self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
                ),
            ):
                load_reference_authentication_enrollment_ed25519_attestor(
                    directory=str(root)
                )
            opened.assert_not_called()

    def test_missing_short_oversized_and_nonregular_key_fail_closed(self) -> None:
        cases = (b"", b"x" * 31, b"x" * 33)
        for value in cases:
            with self.subTest(size=len(value)):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    _write_key(root, value)
                    with self.assertRaises(
                        MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
                    ):
                        load_reference_authentication_enrollment_ed25519_attestor(
                            directory=str(root)
                        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / AUTH_ENROLLMENT_ED25519_KEY_FILENAME
            target.mkdir()
            with self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
            ):
                load_reference_authentication_enrollment_ed25519_attestor(
                    directory=str(root)
                )

    def test_reparse_and_symlink_modes_fail_before_open(self) -> None:
        for marker in ("reparse", "symlink"):
            with self.subTest(marker=marker):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    target = _write_key(root)
                    real_lstat = os.lstat

                    def marked_lstat(path):
                        info = real_lstat(path)
                        if os.fspath(path) == str(target):
                            if marker == "reparse":
                                return _stat_proxy(
                                    info,
                                    st_file_attributes=0x400,
                                )
                            return _stat_proxy(info, st_mode=0o120777)
                        return info

                    with (
                        patch(f"{MODULE}.os.lstat", side_effect=marked_lstat),
                        patch("builtins.open") as opened,
                        self.assertRaises(
                            MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
                        ),
                    ):
                        load_reference_authentication_enrollment_ed25519_attestor(
                            directory=str(root)
                        )
                    opened.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows-only ctime normalization")
    def test_windows_ctime_api_skew_keeps_stable_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "key.bin"
            path.write_bytes(PRIVATE_KEY)
            expected = _identity(os.lstat(path))
            real_fstat = os.fstat

            def skewed_fstat(fd):
                info = real_fstat(fd)
                return _stat_proxy(info, st_ctime_ns=info.st_ctime_ns + 1)

            with patch(f"{MODULE}.os.fstat", side_effect=skewed_fstat):
                self.assertEqual(
                    _read_exact_private_key(str(path), expected),
                    PRIVATE_KEY,
                )

    def test_unstable_handle_or_post_read_path_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "key.bin"
            path.write_bytes(PRIVATE_KEY)
            expected = _identity(os.lstat(path))
            real_fstat = os.fstat
            calls = 0

            def changing_fstat(fd):
                nonlocal calls
                calls += 1
                info = real_fstat(fd)
                if calls == 2:
                    return _stat_proxy(info, st_mtime_ns=info.st_mtime_ns + 1)
                return info

            with (
                patch(f"{MODULE}.os.fstat", side_effect=changing_fstat),
                self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
                ),
            ):
                _read_exact_private_key(str(path), expected)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "key.bin"
            path.write_bytes(PRIVATE_KEY)
            expected = _identity(os.lstat(path))
            real_lstat = os.lstat

            def changed_lstat(target):
                info = real_lstat(target)
                return _stat_proxy(info, st_ctime_ns=info.st_ctime_ns + 1)

            with (
                patch(f"{MODULE}.os.lstat", side_effect=changed_lstat),
                self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
                ),
            ):
                _read_exact_private_key(str(path), expected)

    def test_failure_is_stable_nonreflective_and_constructor_failure_collapses(
        self,
    ) -> None:
        marker = "sensitive-private-key-detail"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_key(root, b"x" * 31)
            with self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
            ) as caught:
                load_reference_authentication_enrollment_ed25519_attestor(
                    directory=str(root)
                )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn(temp_dir, str(caught.exception))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_key(root)
            with (
                patch(
                    f"{MODULE}.MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor",
                    side_effect=RuntimeError(marker),
                ),
                self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileError
                ) as caught,
            ):
                load_reference_authentication_enrollment_ed25519_attestor(
                    directory=str(root)
                )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn(marker, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
