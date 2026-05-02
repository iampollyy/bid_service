import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from bid_service.database import engine, get_db, create_schema, Base
from bid_service.models import Bid, Auction
from bid_service.schemas import (
    BidResponse, BidCreate,
    AuctionResponse, AuctionCreate, AuctionStatusUpdate
)
from bid_service.seed import seed_data
from bid_service.message_sender import message_sender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUSPICIOUS_BID_THRESHOLD = 10000  

app = FastAPI(title="BidService", version="1.0.0")


@app.on_event("startup")
def startup():
    logger.info("Starting BidService — creating schema and tables")
    create_schema()
    Base.metadata.create_all(bind=engine)
    seed_data()
    logger.info("BidService startup complete")


# ==================== BID ENDPOINTS ====================

@app.post("/bids", response_model=BidResponse, status_code=201)
def create_bid(data: BidCreate, db: Session = Depends(get_db)):
    """
    Создаёт ставку и отправляет событие в очередь.
    Триггер: каждый POST /bids → сообщение BidPlaced в Service Bus.
    """
    logger.info("Creating bid: artwork_id=%s user_id=%s amount=%s auction_id=%s",
                 data.artwork_id, data.user_id, data.amount, data.auction_id)
    bid = Bid(**data.model_dump())
    db.add(bid)
    db.commit()
    db.refresh(bid)
    logger.info("Bid created with bid_id=%s", bid.bid_id)

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
    logger.debug("Fetching bid_id=%s", bid_id)
    bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
    if not bid:
        logger.warning("Bid not found: bid_id=%s", bid_id)
        raise HTTPException(status_code=404, detail="Bid not found")
    return bid


@app.get("/bids/artwork/{artwork_id}", response_model=List[BidResponse])
def get_bids_by_artwork(artwork_id: int, db: Session = Depends(get_db)):
    logger.debug("Fetching bids for artwork_id=%s", artwork_id)
    return db.query(Bid).filter(Bid.artwork_id == artwork_id).all()


@app.get("/bids/auction/{auction_id}/status", response_model=List[BidResponse])
def get_bids_by_auction(auction_id: int, db: Session = Depends(get_db)):
    logger.debug("Fetching bids for auction_id=%s", auction_id)
    return db.query(Bid).filter(Bid.auction_id == auction_id).all()


# ==================== AUCTION ENDPOINTS ====================

@app.post("/bids/auction", response_model=AuctionResponse, status_code=201)
def create_auction(data: AuctionCreate, db: Session = Depends(get_db)):
    logger.info("Creating auction: start=%s end=%s status=%s", data.start, data.end, data.status)
    auction = Auction(**data.model_dump())
    db.add(auction)
    db.commit()
    db.refresh(auction)
    logger.info("Auction created with auction_id=%s", auction.auction_id)
    return auction


@app.patch("/bids/auctions/{auction_id}", response_model=AuctionResponse)
def update_auction_status(auction_id: int, data: AuctionStatusUpdate, db: Session = Depends(get_db)):
    """
    Обновляет статус аукциона.
    Если статус = 'completed', отправляет AuctionCompleted в очередь.
    """
    logger.info("Updating auction_id=%s to status='%s'", auction_id, data.status)
    auction = db.query(Auction).filter(Auction.auction_id == auction_id).first()
    if not auction:
        logger.warning("Auction not found: auction_id=%s", auction_id)
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