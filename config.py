import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SERVICE_BUS_SEND_CONNECTION_STRING = os.getenv("SERVICE_BUS_SEND_CONNECTION_STRING", "")

QUEUE_NAME = "polinatrybialustava"
