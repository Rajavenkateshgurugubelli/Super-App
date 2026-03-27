import logging
import time
import uuid
from sqlalchemy.orm import Session
from app.models import DeliveryOrder, DriverProfile, MerchantProfile, Region, Currency
from typing import List, Optional

logger = logging.getLogger(__name__)

class LogisticsService:
    """
    Handles Module 7 (Logistics & Delivery) operations.
    Follows RFC-007 State Machine and Dispatch logic.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_order(
        self, 
        user_id: str, 
        merchant_id: str, 
        pickup: tuple, 
        dropoff: tuple, 
        amount: float, 
        currency: Currency,
        region: Region
    ):
        """
        Initiates a new delivery order in SEARCHING status.
        """
        new_order = DeliveryOrder(
            id=f"ord-{uuid.uuid4()}",
            user_id=user_id,
            merchant_id=merchant_id,
            pickup_lat=pickup[0],
            pickup_lng=pickup[1],
            drop_lat=dropoff[0],
            drop_lng=dropoff[1],
            total_amount=amount,
            currency=currency,
            status="SEARCHING",
            region=region
        )
        self.db.add(new_order)
        self.db.commit()
        self.db.refresh(new_order)
        
        logger.info(f"New order {new_order.id} created for user {user_id} in {region}")
        return new_order

    def assign_driver(self, order_id: str, driver_id: str):
        """
        Transitions order from SEARCHING to ACCEPTED.
        """
        order = self.db.query(DeliveryOrder).filter(
            DeliveryOrder.id == order_id,
            DeliveryOrder.status == "SEARCHING"
        ).first()
        
        if not order:
            logger.warning(f"Order {order_id} not found or already assigned.")
            return None
            
        order.driver_id = driver_id
        order.status = "ACCEPTED"
        self.db.commit()
        
        logger.info(f"Driver {driver_id} assigned to order {order_id}")
        return order

    def update_order_status(self, order_id: str, status: str):
        """
        Handles FSM transitions: ACCEPTED -> ARRIVING -> IN_TRANSIT -> COMPLETED.
        """
        order = self.db.query(DeliveryOrder).filter(
            DeliveryOrder.id == order_id
        ).first()
        
        if not order:
            return None
            
        order.status = status
        if status == "COMPLETED":
            order.completed_at = time.time()
            
        self.db.commit()
        return order

    def get_nearby_merchants(self, lat: float, lng: float, radius_km: float = 5.0) -> List[MerchantProfile]:
        """
        Simple geospatial query for merchants (Fallback for PostGIS/Redis).
        """
        # In a real PostGIS DB: 
        # return db.query(MerchantProfile).filter(func.ST_Distance(...) < radius).all()
        
        # Mocking for local SQLite:
        return self.db.query(MerchantProfile).limit(10).all()

    def get_driver_orders(self, driver_id: str, active_only: bool = True) -> List[DeliveryOrder]:
        """
        Returns history or current active tasks for a driver.
        """
        query = self.db.query(DeliveryOrder).filter(DeliveryOrder.driver_id == driver_id)
        if active_only:
            query = query.filter(DeliveryOrder.status.in_(["ACCEPTED", "ARRIVING", "IN_TRANSIT"]))
        
        return query.order_by(DeliveryOrder.created_at.desc()).all()
