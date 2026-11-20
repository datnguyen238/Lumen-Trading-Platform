from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum,
    Numeric,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OrderSide, OrderType, OrderStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)

    accounts: Mapped[list["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="Main")
    cash_balance: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=100000.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default='USD', server_default='USD')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="accounts")
    positions: Mapped[list["Position"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    trades: Mapped[list["Trade"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class PriceBar(Base):
    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)

    __table_args__ = (
        Index("ix_price_bars_symbol_ts", "symbol", "timestamp", unique=True),
    )


class FxSnapshot:
    native_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(30, 18), nullable=False, default=Decimal('1'), server_default='1')
    fx_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fx_source: Mapped[str] = mapped_column(String(64), nullable=False, default='same_currency', server_default='same_currency')


class Order(FxSnapshot, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)

    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False, default=OrderType.MARKET)

    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    limit_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    filled_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    avg_fill_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="orders")
    trades: Mapped[list["Trade"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    execution: Mapped["ExecutionDetail | None"] = relationship(uselist=False, cascade="all, delete-orphan", back_populates="order")

    @property
    def currency(self) -> str:
        return self.native_currency or self.account.currency

    @property
    def account_currency(self) -> str:
        return self.account.currency


    @property
    def native_total(self):
        return Decimal(self.filled_quantity) * Decimal(self.avg_fill_price) if self.avg_fill_price is not None else None

    @property
    def account_total(self):
        if self.execution:
            return self.execution.account_total
        return Decimal(self.filled_quantity) * Decimal(self.avg_fill_price) * Decimal(self.fx_rate) if self.avg_fill_price is not None else None


class Trade(FxSnapshot, Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)

    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)

    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    account_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="trades")
    order: Mapped["Order"] = relationship(back_populates="trades")

    @property
    def currency(self) -> str:
        return self.native_currency or self.account.currency

    @property
    def account_currency(self) -> str:
        return self.account.currency


    @property
    def native_total(self):
        return Decimal(self.quantity) * Decimal(self.price)

    @property
    def account_total(self):
        return Decimal(self.account_value) if self.account_value is not None else Decimal(self.quantity) * Decimal(self.price) * Decimal(self.fx_rate)

    @property
    def account_price(self):
        return self.account_total / Decimal(self.quantity)


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)

    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    average_price: Mapped[float] = mapped_column(Numeric(30, 14), nullable=False, default=0)

    account: Mapped["Account"] = relationship(back_populates="positions")

    @property
    def currency(self) -> str:
        return self.account.currency

    __table_args__ = (
        Index("ix_positions_account_symbol", "account_id", "symbol", unique=True),
    )

class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    asset_type: Mapped[str] = mapped_column(String, nullable=False, default="stock")  # stock/index/crypto
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserCredential(Base):
    __tablename__ = "user_credentials"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class OrderReceipt(Base):
    __tablename__ = "order_receipts"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    request_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)


class SavedAsset(Base):
    __tablename__ = "saved_assets"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrderPreview(FxSnapshot, Base):
    __tablename__ = "order_previews"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    notional: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    limit_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    quoted_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    quote_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)


class ExecutionDetail(FxSnapshot, Base):
    __tablename__ = "execution_details"
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    quote_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    quote_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    cash_before: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    cash_after: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    fees: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    model: Mapped[str] = mapped_column(String, nullable=False, default="last_observed_price")
    account_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    order: Mapped["Order"] = relationship(back_populates="execution")

    @property
    def currency(self):
        return self.native_currency or self.order.account.currency

    @property
    def account_currency(self):
        return self.order.account.currency

    @property
    def account_total(self):
        return Decimal(self.account_value) if self.account_value is not None else abs(Decimal(self.cash_after) - Decimal(self.cash_before))

    @property
    def account_price(self):
        return self.account_total / Decimal(self.order.filled_quantity)


class AuthRateBucket(Base):
    __tablename__ = "auth_rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class FxRate(Base):
    __tablename__ = 'fx_rates'
    from_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    to_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(30, 18), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
