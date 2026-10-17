"""Tests unitarios de validadores."""

import pytest

from rally.core.exceptions import ValidationException
from rally.utils.validators import (
    validate_device_id,
    validate_ip,
    validate_mac,
    validate_map_position,
    validate_non_negative,
    validate_score,
)


def test_mac_valida():
    assert validate_mac("5A:21:4A:5B:10:01") == "5A:21:4A:5B:10:01"


def test_mac_invalida():
    with pytest.raises(ValidationException):
        validate_mac("SA:21:4A:5B")


def test_ip_valida():
    assert validate_ip("201.213.45.88") == "201.213.45.88"


def test_ip_invalida():
    with pytest.raises(ValidationException):
        validate_ip("999.1.1.1")


def test_device_id():
    assert validate_device_id("camara_remote_04") == "camara_remote_04"
    with pytest.raises(ValidationException):
        validate_device_id("con espacio")


def test_map_position():
    assert validate_map_position(12, 10) == (12.0, 10.0)
    with pytest.raises(ValidationException):
        validate_map_position(120, 10)


def test_score():
    assert validate_score(0.5) == 0.5
    with pytest.raises(ValidationException):
        validate_score(1.5)


def test_non_negative():
    assert validate_non_negative(0, "x") == 0
    with pytest.raises(ValidationException):
        validate_non_negative(-1, "x")
