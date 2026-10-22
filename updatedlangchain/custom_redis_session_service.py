# custom_redis_session_service.py
import redis
import json
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session

import logging
from typing import Optional, List, Any

logger = logging.getLogger(__name__)

class CustomRedisSessionService(BaseSessionService):
    """
    Custom Redis-backed Session Service for Google ADK.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "adk:sessions:",
        ttl_seconds: Optional[int] = 3600,
    ):
        """
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            prefix: Key prefix for session storage
            ttl_seconds: Optional TTL for sessions in seconds
        """
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds
        
        # Create synchronous Redis client
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {host}:{port}/{db}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _session_to_dict(self, session: Session) -> dict:
        """Convert Session to dictionary for JSON storage."""
        return session.model_dump(mode='json')
    
    def _dict_to_session(self, session_dict: dict) -> Session:
        """Convert dictionary back to Session."""
        if 'events' in session_dict:
            events = []
            for event_dict in session_dict['events']:
                events.append(Event(**event_dict))
            session_dict['events'] = events
        return Session(**session_dict)
    
    async def create_session(
        self,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Create a new session in Redis."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state or {}
        )
        
        # Save to Redis
        await self._save_session(session)
        logger.info(f"Session created: {session_id}")
        return session
    
    async def get_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        """Retrieve a session by ID from Redis."""
        key = f"{self.prefix}{session_id}"
        session_data = self.redis_client.get(key)
        
        if not session_data:
            logger.debug(f"Session not found: {session_id}")
            return None
        
        try:
            session_dict = json.loads(session_data)
            session = self._dict_to_session(session_dict)
            
            # Update TTL on access
            if self.ttl_seconds:
                self.redis_client.expire(key, self.ttl_seconds)
            
            logger.debug(f"Session retrieved: {session_id}")
            return session
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to deserialize session {session_id}: {e}")
            return None
    
    async def update_session(self, session: Session) -> None:
        """Update an existing session in Redis."""
        await self._save_session(session)
        logger.info(f"Session updated: {session.id}")
    
    async def delete_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None:
        """Delete a session from Redis."""
        key = f"{self.prefix}{session_id}"
        self.redis_client.delete(key)
        logger.info(f"Session deleted: {session_id}")
    
    async def list_sessions(
        self,
        *,
        app_name: str,
        user_id: Optional[str] = None,
    ) -> ListSessionsResponse:
        """List all sessions for a user."""
        pattern = f"{self.prefix}*"
        session_keys = self.redis_client.keys(pattern)
        
        sessions = []
        for key in session_keys:
            session_data = self.redis_client.get(key)
            if session_data:
                try:
                    session_dict = json.loads(session_data)
                    session = self._dict_to_session(session_dict)
                    # Filter by app_name and user_id
                    if session.app_name == app_name and session.user_id == user_id:
                        sessions.append(session)
                except Exception as e:
                    logger.error(f"Failed to deserialize session from {key}: {e}")
        
        return ListSessionsResponse(sessions=sessions)
    
    async def _save_session(self, session: Session) -> None:
        """Helper method to save session to Redis."""
        session_dict = self._session_to_dict(session)
        session_json = json.dumps(session_dict, default=self._custom_serializer)
        
        key = f"{self.prefix}{session.id}"
        self.redis_client.set(key, session_json)
        
        if self.ttl_seconds:
            self.redis_client.expire(key, self.ttl_seconds)


        logger.debug(f"Session saved to Redis: {session.id} with {len(session.events)} events")

    

    def _custom_serializer(obj: Any) -> Any:
        """Custom JSON serializer for ADK objects."""
        if isinstance(obj, Event):
            return obj.model_dump()
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")