"""
Unit tests for the BidService FastAPI application.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from main import app
from models import Auction, Bid
from message_sender import message_sender as mock_sender


client = TestClient(app)


def _seed_auction(db, status="active", offset_days=0):
    """Insert an auction and return it."""
    auction = Auction(
        start=datetime.utcnow() + timedelta(days=offset_days),
        end=datetime.utcnow() + timedelta(days=offset_days + 7),
        status=status,
    )
    db.add(auction)
    db.commit()
    db.refresh(auction)
    return auction


def _seed_bid(db, auction_id, amount=100.0, user_id=1, artwork_id=1, status="pending"):
    """Insert a bid and return it."""
    bid = Bid(
        artwork_id=artwork_id,
        user_id=user_id,
        amount=amount,
        status=status,
        auction_id=auction_id,
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid



class TestCreateBid:
    """POST /bids"""

    def test_create_bid_success(self, db_session, mock_message_sender):
        auction = _seed_auction(db_session)
        payload = {
            "artwork_id": 1,
            "user_id": 1,
            "amount": 500.0,
            "status": "pending",
            "auction_id": auction.auction_id,
        }
        resp = client.post("/bids", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["amount"] == 500.0
        assert body["auction_id"] == auction.auction_id

        mock_message_sender.send_message.assert_any_call(
            event_type="BidPlaced",
            data=pytest.approx(
                {
                    "bid_id": body["bid_id"],
                    "artwork_id": 1,
                    "user_id": 1,
                    "amount": 500.0,
                    "auction_id": auction.auction_id,
                }
            ),
        )

    def test_create_bid_suspicious(self, db_session, mock_message_sender):
        """Bids over the threshold should trigger SuspiciousBidDetected."""
        auction = _seed_auction(db_session)
        payload = {
            "artwork_id": 2,
            "user_id": 3,
            "amount": 15000.0,  # above SUSPICIOUS_BID_THRESHOLD (10 000)
            "status": "pending",
            "auction_id": auction.auction_id,
        }
        resp = client.post("/bids", json=payload)
        assert resp.status_code == 201

        calls = [c.kwargs.get("event_type") or c.args[0]
                 for c in mock_message_sender.send_message.call_args_list]
        assert "SuspiciousBidDetected" in calls

    def test_create_bid_normal_not_suspicious(self, db_session, mock_message_sender):
        """Bids under the threshold must NOT trigger SuspiciousBidDetected."""
        auction = _seed_auction(db_session)
        payload = {
            "artwork_id": 2,
            "user_id": 3,
            "amount": 100.0,
            "status": "pending",
            "auction_id": auction.auction_id,
        }
        resp = client.post("/bids", json=payload)
        assert resp.status_code == 201

        event_types = [c.kwargs.get("event_type") or c.args[0]
                       for c in mock_message_sender.send_message.call_args_list]
        assert "SuspiciousBidDetected" not in event_types


class TestGetBid:
    """GET /bids/{bid_id}"""

    def test_get_bid_found(self, db_session):
        auction = _seed_auction(db_session)
        bid = _seed_bid(db_session, auction.auction_id, amount=250.0)
        resp = client.get(f"/bids/{bid.bid_id}")
        assert resp.status_code == 200
        assert resp.json()["amount"] == 250.0

    def test_get_bid_not_found(self):
        resp = client.get("/bids/999999")
        assert resp.status_code == 404


class TestGetBidsByArtwork:
    """GET /bids/artwork/{artwork_id}"""

    def test_returns_matching_bids(self, db_session):
        auction = _seed_auction(db_session)
        _seed_bid(db_session, auction.auction_id, artwork_id=10, amount=100)
        _seed_bid(db_session, auction.auction_id, artwork_id=10, amount=200)
        _seed_bid(db_session, auction.auction_id, artwork_id=99, amount=300)

        resp = client.get("/bids/artwork/10")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetBidsByAuction:
    """GET /bids/auction/{auction_id}/status"""

    def test_returns_matching_bids(self, db_session):
        a1 = _seed_auction(db_session)
        a2 = _seed_auction(db_session)
        _seed_bid(db_session, a1.auction_id, amount=100)
        _seed_bid(db_session, a1.auction_id, amount=200)
        _seed_bid(db_session, a2.auction_id, amount=300)

        resp = client.get(f"/bids/auction/{a1.auction_id}/status")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestCreateAuction:
    """POST /bids/auction"""

    def test_create_auction_success(self):
        payload = {
            "start": datetime.utcnow().isoformat(),
            "end": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "status": "active",
        }
        resp = client.post("/bids/auction", json=payload)
        assert resp.status_code == 201
        assert resp.json()["status"] == "active"


class TestUpdateAuctionStatus:
    """PATCH /bids/auctions/{auction_id}"""

    def test_update_status(self, db_session):
        auction = _seed_auction(db_session, status="active")
        resp = client.patch(
            f"/bids/auctions/{auction.auction_id}",
            json={"status": "paused"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_complete_auction_sends_event(self, db_session, mock_message_sender):
        auction = _seed_auction(db_session, status="active")
        _seed_bid(db_session, auction.auction_id, amount=5000, user_id=7)

        resp = client.patch(
            f"/bids/auctions/{auction.auction_id}",
            json={"status": "completed"},
        )
        assert resp.status_code == 200

        event_types = [c.kwargs.get("event_type") or c.args[0]
                       for c in mock_message_sender.send_message.call_args_list]
        assert "AuctionCompleted" in event_types

    def test_update_auction_not_found(self):
        resp = client.patch("/bids/auctions/999999", json={"status": "completed"})
        assert resp.status_code == 404
