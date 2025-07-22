"""
Privacy management service for PICO application.
"""
import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from core.exceptions import PrivacyError
from core.events import event_bus, Event, EventType
from models.enums import PrivacyMode
from utils.logger import get_logger

logger = get_logger(__name__)

class PrivacyManager:
    """
    Manages privacy settings and AI usage tracking for PICO application.
    Uses SQLite database for persistent storage of privacy policies and usage logs.
    """
    
    def __init__(self, db_path: str = "pico_privacy.db"):
        """
        Initialize the privacy manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_dir = Path(db_path).parent
        
        # Ensure database directory exists
        if not self.db_dir.exists():
            self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # In-memory cache for current privacy settings
        self._current_settings: Dict[str, Any] = {}
        
        logger.info(f"PrivacyManager initialized with database: {db_path}")
    
    def set_privacy_mode(self, session_id: str, mode: PrivacyMode) -> None:
        """
        Set privacy mode for a session.
        
        Args:
            session_id: Session identifier
            mode: Privacy mode to set
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if session exists in settings
                cursor.execute(
                    "SELECT id FROM privacy_settings WHERE session_id = ?", 
                    (session_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Update existing settings
                    cursor.execute("""
                        UPDATE privacy_settings 
                        SET mode = ?, updated_at = ?
                        WHERE session_id = ?
                    """, (mode.value, datetime.now().isoformat(), session_id))
                else:
                    # Insert new settings
                    cursor.execute("""
                        INSERT INTO privacy_settings 
                        (session_id, mode, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, mode.value, datetime.now().isoformat(), datetime.now().isoformat()))
                
                conn.commit()
                
                # Update in-memory cache
                self._current_settings[session_id] = {
                    'mode': mode.value,
                    'updated_at': datetime.now().isoformat()
                }
                
                # Publish event
                event_bus.publish(Event(
                    type=EventType.PRIVACY_MODE_CHANGED,
                    data={
                        "session_id": session_id,
                        "mode": mode.value
                    },
                    timestamp=datetime.now().timestamp()
                ))
                
                logger.info(f"Privacy mode set to {mode.value} for session {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to set privacy mode for session {session_id}: {str(e)}")
            raise PrivacyError(f"Failed to set privacy mode for session {session_id}: {str(e)}")
    
    def get_privacy_mode(self, session_id: str) -> PrivacyMode:
        """
        Get current privacy mode for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            PrivacyMode
        """
        # Check in-memory cache first
        if session_id in self._current_settings:
            return PrivacyMode(self._current_settings[session_id]['mode'])
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT mode FROM privacy_settings WHERE session_id = ?", 
                    (session_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    mode = PrivacyMode(result[0])
                    # Cache the result
                    self._current_settings[session_id] = {
                        'mode': mode.value,
                        'updated_at': datetime.now().isoformat()
                    }
                    return mode
                else:
                    # Default to FULL if no setting exists
                    return PrivacyMode.FULL
                    
        except Exception as e:
            logger.error(f"Failed to get privacy mode for session {session_id}: {str(e)}")
            raise PrivacyError(f"Failed to get privacy mode for session {session_id}: {str(e)}")
    
    def check_ai_permission(self, session_id: str, operation: str) -> bool:
        """
        Check if AI processing is allowed for a session.
        
        Args:
            session_id: Session identifier
            operation: Type of AI operation (e.g., 'transcription', 'summarization')
            
        Returns:
            bool: True if AI processing is allowed
        """
        mode = self.get_privacy_mode(session_id)
        
        if mode == PrivacyMode.NONE:
            return False
        elif mode == PrivacyMode.FULL:
            return True
        elif mode == PrivacyMode.SELECTIVE:
            # For SELECTIVE mode, we need user approval
            # This would typically involve a UI prompt, but we'll log the request
            logger.info(f"AI permission requested for session {session_id}, operation: {operation}")
            return False  # Default to deny until user approves
        elif mode == PrivacyMode.METADATA_ONLY:
            # Only allow AI processing on metadata, not content
            return operation == 'metadata_analysis'
        
        return False
    
    def log_ai_usage(self, session_id: str, ai_model: str, operation: str, 
                    input_size: int, output_size: int, cost: float = 0.0) -> int:
        """
        Log AI usage for a session.
        
        Args:
            session_id: Session identifier
            ai_model: AI model used (e.g., 'gpt-4', 'claude')
            operation: Type of operation performed
            input_size: Size of input data (e.g., token count)
            output_size: Size of output data (e.g., token count)
            cost: Cost of the operation (if available)
            
        Returns:
            int: ID of the created log entry
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO ai_usage_log 
                    (session_id, ai_model, operation, input_size, output_size, cost, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session_id, ai_model, operation, input_size, output_size, cost, datetime.now().isoformat()))
                
                log_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"AI usage logged for session {session_id}: {ai_model} - {operation}")
                return log_id
                
        except Exception as e:
            logger.error(f"Failed to log AI usage for session {session_id}: {str(e)}")
            raise PrivacyError(f"Failed to log AI usage for session {session_id}: {str(e)}")
    
    def get_ai_usage_log(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get AI usage log for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of entries to return
            
        Returns:
            List of AI usage log entries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM ai_usage_log 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (session_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get AI usage log for session {session_id}: {str(e)}")
            raise PrivacyError(f"Failed to get AI usage log for session {session_id}: {str(e)}")
    
    def get_usage_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of AI usage.
        
        Args:
            session_id: Optional session identifier (None for all sessions)
            
        Returns:
            Dictionary with usage summary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if session_id:
                    # Summary for specific session
                    cursor.execute("""
                        SELECT 
                            ai_model,
                            operation,
                            COUNT(*) as count,
                            SUM(input_size) as total_input,
                            SUM(output_size) as total_output,
                            SUM(cost) as total_cost
                        FROM ai_usage_log 
                        WHERE session_id = ?
                        GROUP BY ai_model, operation
                    """, (session_id,))
                else:
                    # Summary for all sessions
                    cursor.execute("""
                        SELECT 
                            ai_model,
                            operation,
                            COUNT(*) as count,
                            SUM(input_size) as total_input,
                            SUM(output_size) as total_output,
                            SUM(cost) as total_cost
                        FROM ai_usage_log 
                        GROUP BY ai_model, operation
                    """)
                
                rows = cursor.fetchall()
                
                summary = {
                    'total_entries': sum(row['count'] for row in rows),
                    'total_input': sum(row['total_input'] for row in rows),
                    'total_output': sum(row['total_output'] for row in rows),
                    'total_cost': sum(row['total_cost'] for row in rows),
                    'by_model': {}
                }
                
                for row in rows:
                    model = row['ai_model']
                    if model not in summary['by_model']:
                        summary['by_model'][model] = {
                            'count': 0,
                            'total_input': 0,
                            'total_output': 0,
                            'total_cost': 0,
                            'operations': {}
                        }
                    
                    model_data = summary['by_model'][model]
                    model_data['count'] += row['count']
                    model_data['total_input'] += row['total_input']
                    model_data['total_output'] += row['total_output']
                    model_data['total_cost'] += row['total_cost']
                    
                    op = row['operation']
                    if op not in model_data['operations']:
                        model_data['operations'][op] = {
                            'count': 0,
                            'total_input': 0,
                            'total_output': 0,
                            'total_cost': 0
                        }
                    
                    op_data = model_data['operations'][op]
                    op_data['count'] += row['count']
                    op_data['total_input'] += row['total_input']
                    op_data['total_output'] += row['total_output']
                    op_data['total_cost'] += row['total_cost']
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get AI usage summary: {str(e)}")
            raise PrivacyError(f"Failed to get AI usage summary: {str(e)}")
    
    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect personally identifiable information in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of PII detections with type and location
        """
        detections = []
        
        # Simple PII detection patterns (in practice, use a more sophisticated library)
        import re
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            detections.append({
                'type': 'email',
                'text': match.group(),
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.95
            })
        
        # Phone numbers (simple pattern)
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        for match in re.finditer(phone_pattern, text):
            detections.append({
                'type': 'phone',
                'text': match.group(),
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.85
            })
        
        # Credit card numbers (simple pattern)
        cc_pattern = r'\b(?:\d[ -]*?){13,16}\b'
        for match in re.finditer(cc_pattern, text):
            # Additional validation to reduce false positives
            cc_text = re.sub(r'[^\d]', '', match.group())
            if len(cc_text) in [13, 14, 15, 16] and self._validate_luhn(cc_text):
                detections.append({
                    'type': 'credit_card',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.90
                })
        
        # Names (very basic - in practice use NER)
        # Look for capitalized words that might be names
        name_pattern = r'\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20})?\b'
        for match in re.finditer(name_pattern, text):
            # Filter out common words
            common_words = {'The', 'And', 'But', 'For', 'Not', 'Are', 'Was', 'All', 'Can', 'Had', 'Her', 'She', 'One', 'Our', 'Out', 'Day', 'Get', 'Has', 'Him', 'His', 'How', 'Its', 'Man', 'New', 'Now', 'Old', 'See', 'Two', 'Way', 'Who', 'Boy', 'Did', 'Its', 'Its', 'Let', 'Put', 'Say', 'She', 'Too', 'Use'}
            if match.group() not in common_words:
                detections.append({
                    'type': 'name',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.6
                })
        
        return detections
    
    def get_privacy_settings(self, session_id: str) -> Dict[str, Any]:
        """
        Get complete privacy settings for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with privacy settings
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM privacy_settings WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                else:
                    return {
                        'session_id': session_id,
                        'mode': PrivacyMode.FULL.value,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get privacy settings for session {session_id}: {str(e)}")
            raise PrivacyError(f"Failed to get privacy settings for session {session_id}: {str(e)}")
    
    def update_privacy_settings(self, session_id: str, settings: Dict[str, Any]) -> None:
        """
        Update privacy settings for a session.
        
        Args:
            session_id: Session identifier
            settings: Dictionary with settings to update
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current settings
                current = self.get_privacy_settings(session_id)
                
                # Update with new values
                for key, value in settings.items():
                    if key in current and key not in ['id', 'session_id', 'created_at']:
                        current[key] = value
                
                # Update timestamp
                current['updated_at'] = datetime.now().isoformat()
                
                # Save back to database
                cursor.execute("""
                    UPDATE privacy_settings 
                    SET mode = ?, updated_at = ?
                    WHERE session_id = ?
                """, (current['mode'], current['updated_at'], session_id))
                
                conn.commit()
                
                # Update cache
                self._current_settings[session_id] = {
                    'mode': current['mode'],
                    'updated_at': current['updated_at']
                }
                
                logger.info(f"Privacy settings updated for session {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to update privacy settings for session {session_id}: {str(e)}")
            raise PrivacyError(f"Failed to update privacy settings for session {session_id}: {str(e)}")
    
    # Private helper methods
    
    def _init_database(self) -> None:
        """Initialize the SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create privacy settings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS privacy_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT UNIQUE NOT NULL,
                        mode TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create AI usage log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_usage_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        ai_model TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        input_size INTEGER NOT NULL,
                        output_size INTEGER NOT NULL,
                        cost REAL DEFAULT 0.0,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES privacy_settings (session_id)
                    )
                """)
                
                # Create index for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ai_usage_session 
                    ON ai_usage_log (session_id, timestamp)
                """)
                
                conn.commit()
                
                logger.debug("Privacy database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize privacy database: {str(e)}")
            raise PrivacyError(f"Failed to initialize privacy database: {str(e)}")
    
    def _validate_luhn(self, card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm."""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        
        for d in even_digits:
            checksum += sum(digits_of(d*2))
        
        return checksum % 10 == 0