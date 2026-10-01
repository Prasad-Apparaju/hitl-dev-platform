"""ORM entities for orders (synthetic fixture)."""
from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_no = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False)
    promised_date = Column(Date)
    status = Column(String, nullable=False)
    lines = relationship("OrderLine", back_populates="order")


class OrderLine(Base):
    __tablename__ = "order_lines"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    part_id = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    order = relationship("Order", back_populates="lines")
