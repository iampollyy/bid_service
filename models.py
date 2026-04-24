from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, func
)
from database import Base, SCHEMA

_FK_PREFIX = f"{SCHEMA}." if SCHEMA else ""


class Auction(Base):
    __tablename__ = "Auction"
    __table_args__ = {"schema": SCHEMA}

    auction_id = Column(Integer, primary_key=True, autoincrement=True)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False, default="active")


class Bid(Base):
    __tablename__ = "Bid"
    __table_args__ = {"schema": SCHEMA}

    bid_id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    auction_id = Column(
        Integer,
        ForeignKey(f"{_FK_PREFIX}Auction.auction_id"),
        nullable=False
    )