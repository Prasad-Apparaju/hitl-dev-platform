"""Delivery slots live in the analysts' warehouse (synthetic fixture)."""
from app.settings import WAREHOUSE_DSN


def slots_for(warehouse, order_no):
    table = warehouse.table("delivery_slots")
    return table.select(["slot_id", "order_no", "window_start"]).where(order_no=order_no)
