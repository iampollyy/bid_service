import logging
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
from message_sender import message_sender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUSPICIOUS_BID_THRESHOLD = 10000  

app = FastAPI(title="BidService", version="1.0.0")


@app.on_event("startup")
def startup():
    create_schema()
    Base.metadata.create_all(bind=engine)
    seed_data()


# ==================== BID ENDPOINTS ====================

@app.post("/bids", response_model=BidResponse, status_code=201)
def create_bid(data: BidCreate, db: Session = Depends(get_db)):
    """
    Создаёт ставку и отправляет событие в очередь.
    Триггер: каждый POST /bids → сообщение BidPlaced в Service Bus.
    """
    bid = Bid(**data.model_dump())
    db.add(bid)
    db.commit()
    db.refresh(bid)

    bid_data = {
        "bid_id": bid.bid_id,
        "artwork_id": bid.artwork_id,
        "user_id": bid.user_id,
        "amount": bid.amount,
        "auction_id": bid.auction_id,
    }

    # ТРИГГЕР 1: Отправка события BidPlaced
    message_sender.send_message(event_type="BidPlaced", data=bid_data)
    logger.info(f"BidPlaced event sent for bid {bid.bid_id}")

    # ТРИГГЕР 2: Проверка на подозрительность
    if bid.amount > SUSPICIOUS_BID_THRESHOLD:
        message_sender.send_message(event_type="SuspiciousBidDetected", data=bid_data)
        logger.warning(f"SuspiciousBidDetected event sent for bid {bid.bid_id}")

    return bid


@app.get("/bids/{bid_id}", response_model=BidResponse)
def get_bid(bid_id: int, db: Session = Depends(get_db)):
    bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return bid


@app.get("/bids/artwork/{artwork_id}", response_model=List[BidResponse])
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
    """
    Обновляет статус аукциона.
    Если статус = 'completed', отправляет AuctionCompleted в очередь.
    """
    auction = db.query(Auction).filter(Auction.auction_id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    auction.status = data.status
    db.commit()
    db.refresh(auction)

    # ТРИГГЕР 3: Аукцион завершён
    if data.status.lower() == "completed":
        winning_bid = (
            db.query(Bid)
            .filter(Bid.auction_id == auction_id)
            .order_by(Bid.amount.desc())
            .first()
        )
        event_data = {
            "auction_id": auction.auction_id,
            "artwork_id": winning_bid.artwork_id if winning_bid else None,
            "bid_id": winning_bid.bid_id if winning_bid else None,
            "user_id": winning_bid.user_id if winning_bid else None,
            "amount": winning_bid.amount if winning_bid else None,
        }
        message_sender.send_message(event_type="AuctionCompleted", data=event_data)
        logger.info(f"AuctionCompleted event sent for auction {auction.auction_id}")

    return auction