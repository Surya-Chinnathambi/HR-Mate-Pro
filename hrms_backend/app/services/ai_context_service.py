"""
AI Context Service with Redis for conversation memory.
Stores and retrieves conversation history for contextual AI responses.
"""
import redis
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.config import settings

class AIContextService:
    def __init__(self):
        # Initialize Redis connection
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=True
        )
        self.context_expiry = 86400  # 24 hours in seconds
        
    def _get_context_key(self, session_id: str, date: str) -> str:
        """Generate Redis key for context storage"""
        return f"ai_context:{session_id}:{date}"
    
    def _get_today_key(self, session_id: str) -> str:
        """Get today's context key"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self._get_context_key(session_id, today)
    
    async def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: Unique identifier for the conversation session (e.g., employee_id)
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Additional metadata (function calls, timestamps, etc.)
        """
        try:
            key = self._get_today_key(session_id)
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Get existing messages
            existing = self.redis_client.get(key)
            messages = json.loads(existing) if existing else []
            
            # Append new message
            messages.append(message)
            
            # Store back to Redis with expiry
            self.redis_client.setex(
                key,
                self.context_expiry,
                json.dumps(messages)
            )
            
            return True
        except Exception as e:
            print(f"Error adding message to context: {e}")
            return False
    
    async def get_context(
        self, 
        session_id: str, 
        limit: Optional[int] = 20,
        include_system: bool = True
    ) -> List[Dict]:
        """
        Get conversation context for AI.
        
        Args:
            session_id: Unique identifier for the conversation session
            limit: Maximum number of messages to retrieve
            include_system: Whether to include system messages
            
        Returns:
            List of message dictionaries with role and content
        """
        try:
            # Get today's messages
            today_key = self._get_today_key(session_id)
            today_data = self.redis_client.get(today_key)
            messages = json.loads(today_data) if today_data else []
            
            # Filter out system messages if requested
            if not include_system:
                messages = [m for m in messages if m["role"] != "system"]
            
            # Return last N messages
            return messages[-limit:] if limit else messages
            
        except Exception as e:
            print(f"Error getting context: {e}")
            return []
    
    async def get_context_summary(self, session_id: str) -> Dict:
        """Get summary of conversation context"""
        try:
            today_key = self._get_today_key(session_id)
            data = self.redis_client.get(today_key)
            messages = json.loads(data) if data else []
            
            return {
                "total_messages": len(messages),
                "user_messages": len([m for m in messages if m["role"] == "user"]),
                "assistant_messages": len([m for m in messages if m["role"] == "assistant"]),
                "last_message_time": messages[-1]["timestamp"] if messages else None,
                "session_id": session_id
            }
        except Exception as e:
            print(f"Error getting context summary: {e}")
            return {"total_messages": 0, "error": str(e)}
    
    async def clear_context(self, session_id: str) -> bool:
        """Clear all context for a session"""
        try:
            today_key = self._get_today_key(session_id)
            self.redis_client.delete(today_key)
            return True
        except Exception as e:
            print(f"Error clearing context: {e}")
            return False
    
    async def get_recent_history(
        self, 
        session_id: str, 
        days: int = 7
    ) -> List[Dict]:
        """
        Get conversation history from the past N days.
        
        Args:
            session_id: Unique identifier for the conversation session
            days: Number of days to look back
            
        Returns:
            List of all messages from the past N days
        """
        try:
            all_messages = []
            
            for i in range(days):
                date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                key = self._get_context_key(session_id, date)
                data = self.redis_client.get(key)
                
                if data:
                    messages = json.loads(data)
                    all_messages.extend(messages)
            
            # Sort by timestamp
            all_messages.sort(key=lambda x: x["timestamp"])
            return all_messages
            
        except Exception as e:
            print(f"Error getting recent history: {e}")
            return []
    
    async def format_context_for_ai(
        self, 
        session_id: str,
        system_prompt: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Format context in OpenAI message format.
        
        Args:
            session_id: Unique identifier for the conversation session
            system_prompt: Optional system prompt to prepend
            limit: Maximum number of messages
            
        Returns:
            List formatted for OpenAI API [{"role": "user", "content": "..."}]
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Get conversation history
        context = await self.get_context(session_id, limit=limit)
        
        # Format for OpenAI
        for msg in context:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def health_check(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            return self.redis_client.ping()
        except Exception:
            return False


# Singleton instance
ai_context_service = AIContextService()
