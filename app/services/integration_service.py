import logging
import uuid
import time
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import (
    User, MerchantProfile, HealthRecord, 
    SocialRelationship, FeedActivity, 
    Notification, Region, KycStatus
)
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class IntegrationService:
    """
    Handles Module 8 (Integration & Event Mesh) operations.
    Implements Unified Search and Prioritized Notifications per RFC-008.
    """
    def __init__(self, db: Session):
        self.db = db

    def unified_search(self, user_id: str, query: str, region: Region) -> Dict[str, List[Any]]:
        """
        Performs a global search across all domains: Social, Health, Logistics.
        In production, this would hit an Elasticsearch / OpenSearch cluster.
        """
        results = {
            "people": [],
            "stores": [],
            "medical": []
        }
        
        # 1. Search People (Social)
        people = self.db.query(User).filter(
            User.primary_region == region,
            # In real system: match by name from UserPII via join
            # Mocking by user_id for this standalone demonstration
            User.user_id.contains(query) 
        ).limit(5).all()
        results["people"] = people

        # 2. Search Merchants (Logistics)
        merchants = self.db.query(MerchantProfile).filter(
            MerchantProfile.region == region,
            MerchantProfile.business_name.contains(query)
        ).limit(5).all()
        results["stores"] = merchants

        # 3. Search Medical Providers (Health)
        # Mocking: filter users who have record_type records attributed to them
        results["medical"] = [] 

        logger.info(f"User {user_id} performed unified search for '{query}'")
        return results

    def send_notification(
        self, 
        user_id: str, 
        title: str, 
        body: str, 
        priority: int, 
        domain: str, 
        region: Region
    ):
        """
        Dispatches a prioritized notification.
        P0 = Critical (Security/Emergencies)
        P1 = Transactional (Money/Delivery)
        P2 = Social (Feed/Messaging)
        P3 = Marketing
        """
        new_notif = Notification(
            id=f"notif-{uuid.uuid4()}",
            user_id=user_id,
            title=title,
            body=body,
            priority=priority,
            source_domain=domain,
            region=region
        )
        self.db.add(new_notif)
        self.db.commit()
        self.db.refresh(new_notif)
        
        # In a real system, P0/P1 would trigger immediate Firebase/Apple Push
        if priority <= 1:
            logger.info(f"EMERGENCY/HIGH PRIORITY PUSH: {title} to {user_id}")
        
        return new_notif

    def get_user_notifications(self, user_id: str, unread_only: bool = True):
        """
        Retrieves notifications sorted by priority and recency.
        """
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read == False)
            
        return query.order_by(
            Notification.priority.asc(), 
            Notification.created_at.desc()
        ).all()

    def mark_as_read(self, notification_id: str):
        notif = self.db.query(Notification).filter(Notification.id == notification_id).first()
        if notif:
            notif.is_read = True
            self.db.commit()
            return True
        return False
