"""
Conversation Manager for PakChat
Saves conversations with titles, timestamps, and token counts
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manage user conversations with proper storage"""
    
    def __init__(self, db=None):
        self.db = db  # Database instance (Supabase or SQLite)
        self.logger = logging.getLogger(__name__)
    
    async def save_conversation(self, user_id: str, messages: List[Dict], 
                                model: str = "unknown", tokens: int = 0) -> str:
        """
        Save conversation with auto-generated title from first message
        """
        try:
            # Generate title from first user message
            title = self._generate_title(messages)
            
            conv_id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()
            
            # Try Supabase first
            if self.db and hasattr(self.db, 'supabase') and self.db.supabase:
                try:
                    data = {
                        "id": conv_id,
                        "user_id": user_id,
                        "title": title,
                        "messages": json.dumps(messages),
                        "model": model,
                        "tokens_used": tokens,
                        "created_at": created_at,
                        "updated_at": created_at
                    }
                    
                    result = self.db.supabase.table('conversations').insert(data).execute()
                    if result.data:
                        logger.info(f"✅ Conversation saved to Supabase: {conv_id} - {title}")
                        return conv_id
                except Exception as e:
                    logger.warning(f"⚠️ Supabase save failed: {e}, trying local...")
            
            # Local SQLite fallback
            import aiosqlite
            async with aiosqlite.connect("pakchat.db") as conn:
                await conn.execute("""
                    INSERT INTO conversations 
                    (id, user_id, title, messages, model, tokens_used, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (conv_id, user_id, title, json.dumps(messages), model, tokens, created_at, created_at))
                await conn.commit()
                logger.info(f"✅ Conversation saved locally: {conv_id} - {title}")
                return conv_id
                
        except Exception as e:
            logger.error(f"❌ Failed to save conversation: {e}")
            return None
    
    async def update_conversation(self, conv_id: str, messages: List[Dict], tokens: int = 0):
        """Update existing conversation"""
        try:
            updated_at = datetime.now().isoformat()
            
            if self.db and hasattr(self.db, 'supabase') and self.db.supabase:
                try:
                    self.db.supabase.table('conversations')\
                        .update({
                            "messages": json.dumps(messages),
                            "tokens_used": tokens,
                            "updated_at": updated_at
                        })\
                        .eq('id', conv_id)\
                        .execute()
                    logger.info(f"✅ Conversation updated: {conv_id}")
                    return
                except:
                    pass
            
            # Local fallback
            import aiosqlite
            async with aiosqlite.connect("pakchat.db") as conn:
                await conn.execute("""
                    UPDATE conversations 
                    SET messages = ?, tokens_used = ?, updated_at = ?
                    WHERE id = ?
                """, (json.dumps(messages), tokens, updated_at, conv_id))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Failed to update conversation: {e}")
    
    async def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all conversations for a user"""
        try:
            # Try Supabase
            if self.db and hasattr(self.db, 'supabase') and self.db.supabase:
                try:
                    result = self.db.supabase.table('conversations')\
                        .select('*')\
                        .eq('user_id', user_id)\
                        .order('updated_at', desc=True)\
                        .limit(limit)\
                        .execute()
                    
                    if result.data:
                        # Parse messages JSON
                        for conv in result.data:
                            if isinstance(conv.get('messages'), str):
                                conv['messages'] = json.loads(conv['messages'])
                        return result.data
                except:
                    pass
            
            # Local fallback
            import aiosqlite
            async with aiosqlite.connect("pakchat.db") as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                rows = await cursor.fetchall()
                
                conversations = []
                for row in rows:
                    conv = dict(row)
                    if isinstance(conv.get('messages'), str):
                        conv['messages'] = json.loads(conv['messages'])
                    conversations.append(conv)
                
                return conversations
                
        except Exception as e:
            logger.error(f"❌ Failed to get conversations: {e}")
            return []
    
    async def get_conversation(self, conv_id: str, user_id: str) -> Optional[Dict]:
        """Get single conversation by ID"""
        try:
            # Try Supabase
            if self.db and hasattr(self.db, 'supabase') and self.db.supabase:
                try:
                    result = self.db.supabase.table('conversations')\
                        .select('*')\
                        .eq('id', conv_id)\
                        .eq('user_id', user_id)\
                        .execute()
                    
                    if result.data and len(result.data) > 0:
                        conv = result.data[0]
                        if isinstance(conv.get('messages'), str):
                            conv['messages'] = json.loads(conv['messages'])
                        return conv
                except:
                    pass
            
            # Local fallback
            import aiosqlite
            async with aiosqlite.connect("pakchat.db") as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM conversations 
                    WHERE id = ? AND user_id = ?
                """, (conv_id, user_id))
                row = await cursor.fetchone()
                
                if row:
                    conv = dict(row)
                    if isinstance(conv.get('messages'), str):
                        conv['messages'] = json.loads(conv['messages'])
                    return conv
                
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get conversation: {e}")
            return None
    
    async def delete_conversation(self, conv_id: str, user_id: str) -> bool:
        """Delete a conversation"""
        try:
            # Try Supabase
            if self.db and hasattr(self.db, 'supabase') and self.db.supabase:
                try:
                    self.db.supabase.table('conversations')\
                        .delete()\
                        .eq('id', conv_id)\
                        .eq('user_id', user_id)\
                        .execute()
                    logger.info(f"✅ Conversation deleted: {conv_id}")
                    return True
                except:
                    pass
            
            # Local fallback
            import aiosqlite
            async with aiosqlite.connect("pakchat.db") as conn:
                await conn.execute("""
                    DELETE FROM conversations 
                    WHERE id = ? AND user_id = ?
                """, (conv_id, user_id))
                await conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to delete conversation: {e}")
            return False
    
    def _generate_title(self, messages: List[Dict]) -> str:
        """
        Generate a title from the first user message
        """
        if not messages:
            return "New Conversation"
        
        # Find first user message
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                # Truncate to first 50 chars
                if len(content) > 50:
                    return content[:47] + "..."
                elif content:
                    return content
                break
        
        return "New Conversation"
    
    async def search_conversations(self, user_id: str, query: str) -> List[Dict]:
        """Search conversations by title or content"""
        try:
            # Get all conversations first (simplified)
            conversations = await self.get_user_conversations(user_id, 100)
            
            # Filter by query
            results = []
            query_lower = query.lower()
            
            for conv in conversations:
                # Check title
                if query_lower in conv.get('title', '').lower():
                    results.append(conv)
                    continue
                
                # Check messages
                messages = conv.get('messages', [])
                for msg in messages:
                    if query_lower in msg.get('content', '').lower():
                        results.append(conv)
                        break
            
            return results[:20]  # Limit results
            
        except Exception as e:
            logger.error(f"❌ Failed to search conversations: {e}")
            return []