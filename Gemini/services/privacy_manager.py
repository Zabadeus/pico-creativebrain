"""
Privacy Manager for AI Transcription & Knowledge Management Application

Provides comprehensive privacy control and data sharing transparency:
- Configurable privacy modes (private, selective, open)
- AI provider permissions management
- Real-time data usage tracking and logging
- Content anonymization and sanitization
- GDPR/CCPA compliance features

This module ensures users have complete control over what data is shared
with which AI providers and when.
"""
import hashlib
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict
from models.data_models import Enum
import logging

# Import from centralized models
from models.data_models import (
    PrivacyMode, DataSensitivity, AIProvider, AIUsageLog, PrivacySettings
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PrivacyManager:
    def __init__(self, db_path: str = "privacy_data.db"):
        self.db_path = db_path
        self.settings = self._load_settings() or PrivacySettings(
            mode=PrivacyMode.PRIVATE,
            allowed_providers=[AIProvider.LOCAL],
            auto_anonymize=True,
            require_approval=True,
            max_retention_days=30,
            sensitive_patterns=[
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                r'\(?\b\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b',  # Phone number
            ],
            blocked_content_types=["financial", "medical", "legal"]
        )
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for privacy tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Create privacy settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS privacy_settings (
                        id INTEGER PRIMARY KEY,
                        settings_json TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Create AI usage log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ai_usage_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_hash TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        data_sent_size INTEGER NOT NULL,
                        anonymized BOOLEAN NOT NULL,
                        user_approved BOOLEAN NOT NULL,
                        retention_days INTEGER NOT NULL,
                        expires_at TIMESTAMP NOT NULL
                    )
                ''')
                # Create data inventory table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS data_inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_hash TEXT UNIQUE NOT NULL,
                        content_type TEXT NOT NULL,
                        sensitivity_level TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1,
                        location TEXT NOT NULL,
                        metadata_json TEXT
                    )
                ''')
                conn.commit()
            logger.info("Privacy database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize privacy database: {e}")
            raise

    def set_privacy_mode(self, mode: PrivacyMode) -> bool:
        """Set the global privacy mode"""
        try:
            self.settings.mode = mode
            if mode == PrivacyMode.PRIVATE:
                self.settings.allowed_providers = [AIProvider.LOCAL]
                self.settings.require_approval = True
                self.settings.auto_anonymize = True
            elif mode == PrivacyMode.SELECTIVE:
                self.settings.require_approval = True
                self.settings.auto_anonymize = True
            elif mode == PrivacyMode.OPEN:
                self.settings.allowed_providers = list(AIProvider)
                self.settings.require_approval = False
                self.settings.auto_anonymize = False
            
            self._save_settings()
            logger.info(f"Privacy mode set to {mode.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set privacy mode: {e}")
            return False

    def check_ai_permission(self, content: str, provider: AIProvider, task_type: str) -> Tuple[bool, str]:
        """Check if content can be sent to specific AI provider"""
        try:
            if provider not in self.settings.allowed_providers:
                return False, f"Provider {provider.value} not in allowed list"
            
            if self.settings.mode == PrivacyMode.PRIVATE and provider != AIProvider.LOCAL:
                return False, "Private mode only allows local AI processing"
            
            sensitivity = self._analyze_content_sensitivity(content)
            if sensitivity in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED] and provider != AIProvider.LOCAL:
                return False, f"Content sensitivity level {sensitivity.value} requires local processing only"
            
            content_type = self._classify_content_type(content)
            if content_type in self.settings.blocked_content_types:
                return False, f"Content type {content_type} is blocked from AI processing"
            
            if self.settings.require_approval:
                # In a real implementation, this would prompt the user
                if sensitivity not in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED]:
                    return True, "Permission granted with user approval simulation"
                else:
                    return False, "User approval required for sensitive content"
            
            return True, "Permission granted"
        except Exception as e:
            logger.error(f"Error checking AI permission: {e}")
            return False, f"Error during permission check: {e}"

    def log_ai_usage(self, content: str, provider: AIProvider, task_type: str, 
                     data_sent_size: int, anonymized: bool = False, user_approved: bool = False) -> str:
        """Log AI usage with transparent tracking"""
        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            timestamp = datetime.now()
            expires_at = timestamp + timedelta(days=self.settings.max_retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ai_usage_log 
                    (content_hash, provider, task_type, timestamp, data_sent_size, 
                     anonymized, user_approved, retention_days, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (content_hash, provider.value, task_type, timestamp.isoformat(), 
                      data_sent_size, anonymized, user_approved, 
                      self.settings.max_retention_days, expires_at.isoformat()))
                conn.commit()
            
            logger.info(f"AI usage logged: {provider.value} - {task_type} - {len(content)} chars")
            return content_hash
        except Exception as e:
            logger.error(f"Failed to log AI usage: {e}")
            return ""

    def anonymize_content(self, text: str, anonymization_level: str = "standard") -> Tuple[str, Dict]:
        """Remove or replace identifying information from content"""
        try:
            anonymized_text = text
            replacements = {}
            
            if anonymization_level in ["standard", "aggressive"]:
                for i, pattern in enumerate(self.settings.sensitive_patterns):
                    for match in re.finditer(pattern, anonymized_text):
                        placeholder = f"[REDACTED_{i}]"
                        replacements[match.group(0)] = placeholder
                # Perform replacements after finding all matches to avoid replacing parts of matches
                for original, placeholder in replacements.items():
                    anonymized_text = anonymized_text.replace(original, placeholder)
            
            logger.info(f"Content anonymized: {len(replacements)} replacements made")
            return anonymized_text, replacements
        except Exception as e:
            logger.error(f"Failed to anonymize content: {e}")
            return text, {}

    def get_privacy_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive privacy dashboard information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT provider, COUNT(*), SUM(data_sent_size), 
                           AVG(anonymized), COUNT(CASE WHEN user_approved THEN 1 END)
                    FROM ai_usage_log 
                    WHERE timestamp >= datetime('now', '-30 days')
                    GROUP BY provider
                ''')
                usage_stats = [
                    {'provider': r[0], 'requests': r[1], 'total_data_sent': r[2], 'anonymization_rate': r[3], 'approved_requests': r[4]}
                    for r in cursor.fetchall()
                ]
                
                cursor.execute('''
                    SELECT sensitivity_level, COUNT(*), SUM(access_count)
                    FROM data_inventory
                    GROUP BY sensitivity_level
                ''')
                data_inventory = [
                    {'sensitivity': r[0], 'items': r[1], 'total_accesses': r[2]}
                    for r in cursor.fetchall()
                ]
            
            return {
                'privacy_mode': self.settings.mode.value,
                'settings': asdict(self.settings, dict_factory=lambda x: {k: v.value if isinstance(v, Enum) else v for k, v in x}),
                'usage_statistics': usage_stats,
                'data_inventory': data_inventory,
                'recent_activity': self._get_recent_activity(),
                'privacy_score': self._calculate_privacy_score(),
                'recommendations': self._get_privacy_recommendations()
            }
        except Exception as e:
            logger.error(f"Failed to get privacy dashboard data: {e}")
            return {}

    def cleanup_expired_data(self) -> int:
        """Clean up expired data according to retention policies"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ai_usage_log WHERE expires_at < datetime('now')")
                expired_logs = cursor.rowcount
                
                cursor.execute("DELETE FROM data_inventory WHERE created_at < datetime('now', '-' || ? || ' days')", (self.settings.max_retention_days,))
                expired_inventory = cursor.rowcount
                conn.commit()
            
            total_cleaned = expired_logs + expired_inventory
            logger.info(f"Cleaned up {total_cleaned} expired data records")
            return total_cleaned
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0

    def _analyze_content_sensitivity(self, content: str) -> DataSensitivity:
        """Analyze content to determine sensitivity level"""
        content_lower = content.lower()
        sensitive_keywords = ['confidential', 'classified', 'secret', 'private', 'medical', 'health', 'diagnosis', 'treatment', 'financial', 'bank', 'account', 'salary', 'income', 'legal', 'lawsuit', 'attorney', 'court']
        has_sensitive_patterns = any(re.search(pattern, content) for pattern in self.settings.sensitive_patterns)
        has_sensitive_keywords = any(keyword in content_lower for keyword in sensitive_keywords)
        
        if has_sensitive_patterns and has_sensitive_keywords:
            return DataSensitivity.RESTRICTED
        elif has_sensitive_patterns or has_sensitive_keywords:
            return DataSensitivity.CONFIDENTIAL
        elif any(word in content_lower for word in ['personal', 'private', 'individual']):
            return DataSensitivity.PERSONAL
        else:
            return DataSensitivity.PUBLIC

    def _classify_content_type(self, content: str) -> str:
        """Classify content into categories"""
        content_lower = content.lower()
        if any(word in content_lower for word in ['medical', 'health', 'doctor', 'diagnosis']):
            return 'medical'
        elif any(word in content_lower for word in ['financial', 'bank', 'money', 'investment']):
            return 'financial'
        elif any(word in content_lower for word in ['legal', 'law', 'court', 'attorney']):
            return 'legal'
        elif any(word in content_lower for word in ['business', 'company', 'corporate']):
            return 'business'
        else:
            return 'general'

    def _save_settings(self):
        """Save current settings to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                settings_json = json.dumps(asdict(self.settings), default=lambda o: o.value if isinstance(o, Enum) else o)
                cursor.execute("INSERT OR REPLACE INTO privacy_settings (id, settings_json, updated_at) VALUES (1, ?, datetime('now'))", (settings_json,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _load_settings(self) -> Optional[PrivacySettings]:
        """Load settings from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT settings_json FROM privacy_settings WHERE id = 1")
                row = cursor.fetchone()
                if row:
                    settings_data = json.loads(row[0])
                    # Convert string values back to Enums
                    settings_data['mode'] = PrivacyMode(settings_data['mode'])
                    settings_data['allowed_providers'] = [AIProvider(p) for p in settings_data['allowed_providers']]
                    return PrivacySettings(**settings_data)
        except Exception as e:
            logger.error(f"Could not load settings from DB, using defaults. Error: {e}")
        return None

    def _get_recent_activity(self) -> List[Dict]:
        """Get recent privacy-related activity"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT provider, task_type, timestamp, anonymized, user_approved
                    FROM ai_usage_log
                    WHERE timestamp >= datetime('now', '-7 days')
                    ORDER BY timestamp DESC
                    LIMIT 20
                ''')
                return [{'provider': r[0], 'task_type': r[1], 'timestamp': r[2], 'anonymized': bool(r[3]), 'user_approved': bool(r[4])} for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}")
            return []

    def _calculate_privacy_score(self) -> int:
        """Calculate a privacy score (0-100) based on current settings and usage"""
        score = 0
        if self.settings.mode == PrivacyMode.PRIVATE: score += 40
        elif self.settings.mode == PrivacyMode.SELECTIVE: score += 25
        else: score += 10
        if self.settings.auto_anonymize: score += 15
        if self.settings.require_approval: score += 15
        if len(self.settings.allowed_providers) == 1 and AIProvider.LOCAL in self.settings.allowed_providers: score += 15
        elif len(self.settings.allowed_providers) <= 2: score += 10
        if self.settings.max_retention_days <= 30: score += 10
        elif self.settings.max_retention_days <= 90: score += 5
        return min(100, score)

    def _get_privacy_recommendations(self) -> List[str]:
        """Get personalized privacy recommendations"""
        recommendations = []
        if self.settings.mode != PrivacyMode.PRIVATE:
            recommendations.append("Consider switching to Private mode for maximum privacy protection.")
        if not self.settings.auto_anonymize:
            recommendations.append("Enable auto-anonymization to protect sensitive information.")
        if self.settings.max_retention_days > 30:
            recommendations.append("Reduce data retention period to 30 days or less.")
        if len(self.settings.allowed_providers) > 3:
            recommendations.append("Limit the number of allowed AI providers to reduce data exposure.")
        return recommendations
