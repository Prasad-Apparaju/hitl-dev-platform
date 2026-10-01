"""Order repository (synthetic fixture)."""
from app.models.order import Order


def open_orders(session, tenant_id):
    return session.query(Order).filter(Order.tenant_id == tenant_id, Order.status == "open").all()
