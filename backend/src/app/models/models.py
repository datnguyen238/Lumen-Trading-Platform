from datetime import datetime
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="accounts")
    positions: Mapped[list["Position"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    trades: Mapped[list["Trade"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class PriceBar(Base):
    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)

    __table_args__ = (
        Index("ix_price_bars_symbol_ts", "symbol", "timestamp", unique=True),
    )


class Order(Base):
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


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)

    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)

    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped["Account"] = relationship(back_populates="trades")
    order: Mapped["Order"] = relationship(back_populates="trades")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)

    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    average_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)

    account: Mapped["Account"] = relationship(back_populates="positions")

    __table_args__ = (
        Index("ix_positions_account_symbol", "account_id", "symbol", unique=True),
    )
