from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import engine, get_db, create_schema, Base
from models import Bid, Auction
from schemas import (
    BidResponse, BidCreate,
    AuctionResponse, AuctionCreate, AuctionStatusUpdate
)
from seed import seed_data

app = FastAPI(title="BidService", version="1.0.0")


@app.on_event("startup")
def startup():
    create_schema()
    Base.metadata.create_all(bind=engine)
    seed_data()


# ==================== BID ENDPOINTS ====================

@app.post("/bids", response_model=BidResponse, status_code=201)
def create_bid(data: BidCreate, db: Session = Depends(get_db)):
    bid = Bid(**data.model_dump())
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


@app.get("/bids/{bid_id}", response_model=BidResponse)
def get_bid(bid_id: int, db: Session = Depends(get_db)):
    bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return bid


@app.get("/bids/{artwork_id}", response_model=List[BidResponse])
def get_bids_by_artwork(artwork_id: int, db: Session = Depends(get_db)):
    return db.query(Bid).filter(Bid.artwork_id == artwork_id).all()


@app.get("/bids/auction/{auction_id}/status", response_model=List[BidResponse])
def get_bids_by_auction(auction_id: int, db: Session = Depends(get_db)):
    return db.query(Bid).filter(Bid.auction_id == auction_id).all()


# ==================== AUCTION ENDPOINTS ====================

@app.post("/bids/auction", response_model=AuctionResponse, status_code=201)
def create_auction(data: AuctionCreate, db: Session = Depends(get_db)):
    auction = Auction(**data.model_dump())
    db.add(auction)
    db.commit()
    db.refresh(auction)
    return auction


@app.patch("/bids/auctions/{auction_id}", response_model=AuctionResponse)
def update_auction_status(auction_id: int, data: AuctionStatusUpdate, db: Session = Depends(get_db)):
    auction = db.query(Auction).filter(Auction.auction_id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    auction.status = data.status
    db.commit()
    db.refresh(auction)
    return auction