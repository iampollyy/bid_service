import logging
from datetime import datetime, timedelta
from bid_service.database import SessionLocal
from bid_service.models import Auction, Bid

logger = logging.getLogger(__name__)


def seed_data():
    db = SessionLocal()
    try:
        if db.query(Auction).first():
            logger.info("Seed data already exists — skipping")
            return

        auctions = [
            Auction(
                start=datetime.utcnow(),
                end=datetime.utcnow() + timedelta(days=7),
                status="active"
            ),
            Auction(
                start=datetime.utcnow() - timedelta(days=14),
                end=datetime.utcnow() - timedelta(days=7),
                status="completed"
            ),
            Auction(
                start=datetime.utcnow() + timedelta(days=1),
                end=datetime.utcnow() + timedelta(days=10),
                status="scheduled"
            ),
        ]
        db.add_all(auctions)
        db.flush()  

        bids = [
            Bid(artwork_id=1, user_id=1, amount=500.00, status="active", auction_id=auctions[0].auction_id),
            Bid(artwork_id=1, user_id=2, amount=750.00, status="active", auction_id=auctions[0].auction_id),
            Bid(artwork_id=2, user_id=3, amount=1200.00, status="won", auction_id=auctions[1].auction_id),
            Bid(artwork_id=2, user_id=1, amount=1000.00, status="outbid", auction_id=auctions[1].auction_id),
            Bid(artwork_id=3, user_id=2, amount=300.00, status="pending", auction_id=auctions[2].auction_id),
        ]
        db.add_all(bids)
        db.commit()
        logger.info("Seed data added successfully (%d auctions, %d bids)", len(auctions), len(bids))
    except Exception as e:
        db.rollback()
        logger.error("Error during seed: %s", e, exc_info=True)
    finally:
        db.close()