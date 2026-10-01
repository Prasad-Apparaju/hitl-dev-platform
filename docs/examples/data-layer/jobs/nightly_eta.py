"""Nightly job: recompute each open order's ETA into the eta_cache collection (synthetic fixture)."""
from statistics import median

from pymongo import MongoClient
from sqlalchemy import select

from app.models.order import Order
from app.settings import MONGO_URI

db = MongoClient(MONGO_URI).get_default_database()
rows = session.execute(select(Order.order_no, Order.promised_date).where(Order.status == "open")).all()
lag_days = median(carrier_lags_last_30_days())

ships = {s["order_no"]: s for s in db["shipments"].find({}, {"order_no": 1, "carrier_ref": 1, "shipped_at": 1})}

for order_no, promised in rows:
    eta = promised + lag_days
    cache = db["eta_cache"]
    key = {"order_no": order_no}
    cache.update_one(key, {"$set": {"eta": eta, "computed_at": now()}}, upsert=True)
