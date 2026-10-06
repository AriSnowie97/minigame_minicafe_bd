"""
ORM-моделі MiniCafe (SQLAlchemy 2.0).

Кожен клас відповідає таблиці з database/schema_postgres.sql, а зв'язки між
таблицями описані через relationship() — з них будуються складні запити у stats.py.
"""
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric,
                        String, Text, UniqueConstraint, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Гроші повертаємо як float (а не Decimal): так однаково працює і PostgreSQL, і SQLite
Money = Numeric(8, 2, asdecimal=False)


class Base(DeclarativeBase):
    pass


class MenuCategory(Base):
    __tablename__ = "menucategories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    items: Mapped[List["MenuItem"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    unitprice: Mapped[float] = mapped_column(Money, nullable=False)
    shelflifedays: Mapped[Optional[int]] = mapped_column(Integer)

    ingredients: Mapped[List["MenuItemIngredient"]] = relationship(back_populates="product")


class MenuItem(Base):
    __tablename__ = "menuitems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    categoryid: Mapped[int] = mapped_column(ForeignKey("menucategories.id"), nullable=False)
    price: Mapped[float] = mapped_column(Money, nullable=False)
    cookingtimemin: Mapped[int] = mapped_column(Integer, nullable=False)
    recipe: Mapped[Optional[str]] = mapped_column(Text)

    category: Mapped["MenuCategory"] = relationship(back_populates="items")
    ingredients: Mapped[List["MenuItemIngredient"]] = relationship(
        back_populates="menu_item", cascade="all, delete-orphan")
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="menu_item")


class MenuItemIngredient(Base):
    """Склад страви: зв'язок «багато до багатьох» MenuItem <-> Product"""
    __tablename__ = "menuitemingredients"
    __table_args__ = (UniqueConstraint("menuitemid", "productid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    menuitemid: Mapped[int] = mapped_column(ForeignKey("menuitems.id", ondelete="CASCADE"), nullable=False)
    productid: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(6, 3, asdecimal=False), nullable=False)

    menu_item: Mapped["MenuItem"] = relationship(back_populates="ingredients")
    product: Mapped["Product"] = relationship(back_populates="ingredients")


class CafeTable(Base):
    __tablename__ = "cafetables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    tablenumber: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(30))

    orders: Mapped[List["Order"]] = relationship(back_populates="table")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    fullname: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    hiredate: Mapped[date] = mapped_column(Date, nullable=False)

    orders: Mapped[List["Order"]] = relationship(back_populates="employee")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("status IN ('відкрито', 'оплачено', 'скасовано')"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tableid: Mapped[int] = mapped_column(ForeignKey("cafetables.id"), nullable=False)
    employeeid: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    orderdatetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="відкрито")
    gameday: Mapped[Optional[int]] = mapped_column(Integer)   # ігровий день, у який зроблено замовлення

    table: Mapped["CafeTable"] = relationship(back_populates="orders")
    employee: Mapped["Employee"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "orderitems"
    __table_args__ = (UniqueConstraint("orderid", "menuitemid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    orderid: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    menuitemid: Mapped[int] = mapped_column(ForeignKey("menuitems.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    priceatorder: Mapped[float] = mapped_column(Money, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship(back_populates="order_items")
