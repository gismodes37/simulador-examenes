import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
class TestUserCreation:
    def test_create_user_without_callsign(self):
        user = User.objects.create_user(
            username="novice1",
            email="novice1@example.com",
            password="testpass123",
        )
        assert user.username == "novice1"
        assert user.email == "novice1@example.com"
        assert user.callsign is None
        assert user.is_radio_amateur is False
        assert user.check_password("testpass123")

    def test_create_user_with_callsign(self):
        user = User.objects.create_user(
            username="xq1aa",
            email="xq1aa@example.com",
            password="testpass123",
            callsign="XQ1AA",
            is_radio_amateur=True,
        )
        assert user.callsign == "XQ1AA"
        assert user.is_radio_amateur is True
        assert str(user) == "XQ1AA (xq1aa)"

    def test_create_user_without_callsign_str(self):
        user = User.objects.create_user(
            username="pedro",
            email="pedro@example.com",
            password="testpass123",
        )
        assert str(user) == "pedro"

    def test_duplicate_callsign_rejected(self):
        User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="pass123",
            callsign="XQ1AA",
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="user2",
                email="user2@example.com",
                password="pass123",
                callsign="XQ1AA",
            )

    def test_duplicate_email_allowed(self):
        """Django's AbstractUser doesn't enforce unique email by default."""
        User.objects.create_user(
            username="user1",
            email="same@example.com",
            password="pass123",
        )
        user2 = User.objects.create_user(
            username="user2",
            email="same@example.com",
            password="pass123",
        )
        assert user2.email == "same@example.com"

    def test_user_str_with_callsign(self):
        user = User.objects.create_user(
            username="lu1aaa",
            callsign="LU1AAA",
            password="pass123",
        )
        assert str(user) == "LU1AAA (lu1aaa)"

    def test_user_str_without_callsign(self):
        user = User.objects.create_user(
            username="maria",
            password="pass123",
        )
        assert str(user) == "maria"
