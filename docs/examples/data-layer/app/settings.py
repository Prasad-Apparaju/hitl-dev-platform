import os

DATABASE_URL = os.environ["DATABASE_URL"]
MONGO_URI = os.environ["MONGO_URI"]
WAREHOUSE_DSN = os.environ.get("WAREHOUSE_DSN")  # analysts' warehouse; app reads delivery slots from it
