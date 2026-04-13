from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# --- Auction ---
class AuctionBase(BaseModel):
    start: datetime
    end: datetime
    status: str = "active"


class AuctionCreate(AuctionBase):
    pass


class AuctionStatusUpdate(BaseModel):
    status: str


class AuctionResponse(AuctionBase):
    auction_id: int

    class Config:
        from_attributes = True


# --- Bid ---
class BidBase(BaseModel):
    artwork_id: int
    user_id: int
    amount: float
    status: str = "pending"
    auction_id: int


class BidCreate(BidBase):
    pass


class BidResponse(BidBase):
    bid_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True