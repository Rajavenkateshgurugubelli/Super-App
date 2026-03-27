import logging
import time
import json
import uuid
from sqlalchemy.orm import Session
from app.models import SocialRelationship, FeedActivity, User, Region
from typing import List, Optional

logger = logging.getLogger(__name__)

class SocialService:
    """
    Handles Module 5 (Social Media) backend operations.
    Follows RFC-005 specifications for social graph and activity feed.
    """
    def __init__(self, db: Session):
        self.db = db

    def follow_user(self, follower_id: str, followed_id: str, region: Region):
        """
        Creates a 'FOLLOW' relationship between two users.
        """
        # Logic check: prevent self-follow
        if follower_id == followed_id:
            raise ValueError("Cannot follow yourself.")

        # Check if already exists
        existing = self.db.query(SocialRelationship).filter(
            SocialRelationship.follower_id == follower_id,
            SocialRelationship.followed_id == followed_id,
            SocialRelationship.type == "FOLLOW"
        ).first()

        if existing:
            return existing

        new_rel = SocialRelationship(
            id=f"rel_{uuid.uuid4().hex[:8]}",
            follower_id=follower_id,
            followed_id=followed_id,
            type="FOLLOW",
            region=region
        )
        self.db.add(new_rel)
        self.db.commit()
        self.db.refresh(new_rel)
        
        logger.info(f"User {follower_id} followed {followed_id} in {region}")
        return new_rel

    def unfollow_user(self, follower_id: str, followed_id: str):
        """
        Removes a follow relationship.
        """
        rel = self.db.query(SocialRelationship).filter(
            SocialRelationship.follower_id == follower_id,
            SocialRelationship.followed_id == followed_id,
            SocialRelationship.type == "FOLLOW"
        ).first()

        if rel:
            self.db.delete(rel)
            self.db.commit()
            return True
        return False

    def block_user(self, blocker_id: str, blocked_id: str, region: Region):
        """
        Creates a 'BLOCK' relationship and removes existing follow connections.
        """
        # 1. Clear any existing follows
        self.unfollow_user(blocker_id, blocked_id)
        self.unfollow_user(blocked_id, blocker_id)

        new_block = SocialRelationship(
            id=f"blk_{uuid.uuid4().hex[:8]}",
            follower_id=blocker_id,
            followed_id=blocked_id,
            type="BLOCK",
            region=region
        )
        self.db.add(new_block)
        self.db.commit()
        return new_block

    def create_post(self, user_id: str, content: str, media_url: Optional[str], region: Region):
        """
        Creates a new activity feed item.
        """
        new_activity = FeedActivity(
            id=f"act_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            activity_type="POST",
            content=content, # Can be raw text or JSON
            media_url=media_url,
            region=region
        )
        self.db.add(new_activity)
        self.db.commit()
        self.db.refresh(new_activity)
        return new_activity

    def get_user_feed(self, user_id: str, limit: int = 20):
        """
        Retrieves feed items from users being followed.
        """
        # 1. Get list of followed IDs
        followed_ids = self.db.query(SocialRelationship.followed_id).filter(
            SocialRelationship.follower_id == user_id,
            SocialRelationship.type == "FOLLOW"
        ).all()
        
        followed_ids = [f[0] for f in followed_ids]
        
        # Always include own posts
        followed_ids.append(user_id)

        # 2. Query FeedActivity
        feed = self.db.query(FeedActivity).filter(
            FeedActivity.user_id.in_(followed_ids)
        ).order_by(FeedActivity.created_at.desc()).limit(limit).all()

        return feed

    def get_followers(self, user_id: str) -> List[User]:
        """Returns users following the target user."""
        rels = self.db.query(SocialRelationship).filter(
            SocialRelationship.followed_id == user_id,
            SocialRelationship.type == "FOLLOW"
        ).all()
        return [r.follower for r in rels]

    def get_following(self, user_id: str) -> List[User]:
        """Returns users the target user is following."""
        rels = self.db.query(SocialRelationship).filter(
            SocialRelationship.follower_id == user_id,
            SocialRelationship.type == "FOLLOW"
        ).all()
        return [r.followed for r in rels]
