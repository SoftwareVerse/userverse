import sys
import runpy

import pytest

from app.utils.hash_password import (
    UnknownHashError,
    _is_bcrypt_hash,
    hash_password,
    verify_password,
)


def test_hash_password_and_verify_password_round_trip():
    hashed = hash_password("MyS3cret!")

    assert hashed != "MyS3cret!"
    assert verify_password("MyS3cret!", hashed) is True
    assert verify_password("WrongPass", hashed) is False


def test_hash_password_rejects_empty_or_non_string_values():
    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password("")

    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password(None)


def test_verify_password_rejects_unknown_hashes():
    with pytest.raises(UnknownHashError, match="hash could not be identified"):
        verify_password("secret", "plaintext-password")


def test_is_bcrypt_hash_handles_non_strings_and_short_values():
    assert _is_bcrypt_hash(None) is False
    assert _is_bcrypt_hash("$2b$short") is False


def test_hash_password_module_demo_runs_as_main(capsys):
    module_name = "app.utils.hash_password"
    original_module = sys.modules.pop(module_name, None)

    try:
        runpy.run_module(module_name, run_name="__main__")
    finally:
        if original_module is not None:
            sys.modules[module_name] = original_module

    output = capsys.readouterr().out
    assert "Password:" in output
    assert "Verify (correct): True" in output
