"""Shipment lookups against the document store (synthetic fixture)."""
from pymongo import MongoClient

from app.settings import MONGO_URI

db = MongoClient(MONGO_URI).get_default_database()
shipments = db["shipments"]


def shipments_for(orders):
    nos = [o.order_no for o in orders]
    return list(shipments.find({"order_no": {"$in": nos}}, {"order_no": 1, "carrier_ref": 1, "eta": 1}))
