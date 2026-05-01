from unittest.mock import patch
from datetime import datetime

from app.services.hours import is_store_open_now
from app.core.security import hash_password, verify_password


class DummyStore:
    hours_mon = "08:00-22:00"
    hours_tue = "08:00-22:00"
    hours_wed = "08:00-22:00"
    hours_thu = "08:00-22:00"
    hours_fri = "08:00-22:00"
    hours_sat = "closed"
    hours_sun = "10:00-20:00"


def test_password_hash_and_verify_success():
    password = "TestPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True


def test_password_verify_failure():
    password = "TestPassword123!"
    wrong_password = "WrongPassword123!"
    hashed = hash_password(password)

    assert verify_password(wrong_password, hashed) is False


def test_is_store_open_now_true():
    fake_now = datetime(2026, 5, 4, 12, 0, 0)  # Monday

    with patch("app.services.hours.datetime") as mock_datetime:
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        assert is_store_open_now(DummyStore()) is True


def test_is_store_open_now_false_when_closed_day():
    fake_now = datetime(2026, 5, 9, 12, 0, 0)  # Saturday

    with patch("app.services.hours.datetime") as mock_datetime:
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        assert is_store_open_now(DummyStore()) is False


def test_is_store_open_now_false_outside_hours():
    fake_now = datetime(2026, 5, 4, 23, 0, 0)  # Monday 23:00

    with patch("app.services.hours.datetime") as mock_datetime:
        mock_datetime.now.return_value = fake_now
        mock_datetime.strptime = datetime.strptime

        assert is_store_open_now(DummyStore()) is False