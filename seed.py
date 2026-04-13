from datetime import datetime, timedelta
from database import SessionLocal
from models import Auction, Bid


def seed_data():
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже данные
        if db.query(Auction).first():
            print("[BidService] Data already exists, skipping seed.")
            return

        # Создаём аукционы
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
        db.flush()  # чтобы получить id

        # Создаём ставки
        bids = [
            Bid(artwork_id=1, user_id=1, amount=500.00, status="active", auction_id=auctions[0].auction_id),
            Bid(artwork_id=1, user_id=2, amount=750.00, status="active", auction_id=auctions[0].auction_id),
            Bid(artwork_id=2, user_id=3, amount=1200.00, status="won", auction_id=auctions[1].auction_id),
            Bid(artwork_id=2, user_id=1, amount=1000.00, status="outbid", auction_id=auctions[1].auction_id),
            Bid(artwork_id=3, user_id=2, amount=300.00, status="pending", auction_id=auctions[2].auction_id),
        ]
        db.add_all(bids)
        db.commit()
        print("[BidService] Seed data added successfully!")
    except Exception as e:
        db.rollback()
        print(f"[BidService] Error during seed: {e}")
    finally:
        db.close()