from decimal import Decimal

import pytest

from alphaedge.modules.identity.application.services import PasswordService
from alphaedge.modules.identity.domain.entities import Role, RoleName, User
from alphaedge.shared.domain.exceptions import ValidationError
from alphaedge.shared.domain.value_objects import Money, Price, Quantity, Symbol


class TestValueObjects:
    def test_money_valid(self):
        m = Money(Decimal("100.50"), "USD")
        assert m.amount == Decimal("100.50")
        assert m.currency == "USD"

    def test_money_negative_raises(self):
        with pytest.raises(ValueError):
            Money(Decimal("-1"))

    def test_price_valid(self):
        p = Price(Decimal("190.25"))
        assert p.value == Decimal("190.25")

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValueError):
            Quantity(Decimal("0"))

    def test_symbol_valid(self):
        s = Symbol("AAPL", "NASDAQ")
        assert s.ticker == "AAPL"


class TestUserEntity:
    def test_create_user(self):
        user = User.create("test@example.com", "hashed", "Test User")
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            User.create("invalid", "hash", "Name")

    def test_has_permission_trader(self):
        user = User.create("t@example.com", "hash", "Trader")
        user.roles = [Role(id=User.create("x@y.com", "h", "X").id, name=RoleName.TRADER)]
        assert user.has_permission("read:strategies")
        assert user.has_permission("write:backtests")
        assert not user.has_permission("admin:users")

    def test_has_permission_admin(self):
        user = User.create("a@example.com", "hash", "Admin")
        user.roles = [Role(id=User.create("x@y.com", "h", "X").id, name=RoleName.ADMIN)]
        assert user.has_permission("anything:at_all")


class TestPasswordService:
    def test_hash_and_verify(self):
        hashed = PasswordService.hash("SecurePassword1234")
        assert PasswordService.verify("SecurePassword1234", hashed)
        assert not PasswordService.verify("WrongPassword1234", hashed)
