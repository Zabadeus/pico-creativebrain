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
# backend/privacy/privacy_manager.py
import hashlib
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PrivacyMode(Enum):
    PRIVATE = "private"      # No AI processing, local only
    SELECTIVE = "selective"  # User controls what goes to AI
    OPEN = "open"           # All content can be processed by AI

class DataSensitivity(Enum):
    PUBLIC = "public"        # Can be shared freely
    PERSONAL = "personal"    # Contains personal information
    CONFIDENTIAL = "confidential"  # Sensitive business/private data
    RESTRICTED = "restricted"      # Must not be shared externally

class AIProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    HUGGINGFACE = "huggingface"
    OPENROUTER = "openrouter"
    LOCAL = "local"

@dataclass
class AIUsageLog:
    content_hash: str
    provider: AIProvider
    task_type: str
    timestamp: datetime
    data_sent_size: int
    anonymized: bool
    user_approved: bool
    retention_days: int

@dataclass
class PrivacySettings:
    mode: PrivacyMode
    allowed_providers: List[AIProvider]
    auto_anonymize: bool
    require_approval: bool
    max_retention_days: int
    sensitive_patterns: List[str]
    blocked_content_types: List[str]

class PrivacyManager:
    def __init__(self, db_path: str = "privacy_data.db"):
        self.db_path = db_path
        self.privacy_mode = PrivacyMode.PRIVATE
        self.settings = PrivacySettings(
            mode=PrivacyMode.PRIVATE,
            allowed_providers=[AIProvider.LOCAL],
            auto_anonymize=True,
            require_approval=True,
            max_retention_days=30,
            sensitive_patterns=[
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # Credit card
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                r'\b\d{3}-\d{3}-\d{4}\b',  # Phone number
            ],
            blocked_content_types=["financial", "medical", "legal"]
        )
        self.usage_log: List[AIUsageLog] = []
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for privacy tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create privacy settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS privacy_settings (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL,
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
            conn.close()
            logger.info("Privacy database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize privacy database: {e}")
            raise

    def set_privacy_mode(self, mode: PrivacyMode) -> bool:
        """Set the global privacy mode"""
        try:
            self.privacy_mode = mode
            self.settings.mode = mode
            
            # Update default settings based on mode
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
            # Check if provider is allowed
            if provider not in self.settings.allowed_providers:
                return False, f"Provider {provider.value} not in allowed list"
            
            # Check privacy mode restrictions
            if self.privacy_mode == PrivacyMode.PRIVATE and provider != AIProvider.LOCAL:
                return False, "Private mode only allows local AI processing"
            
            # Check content sensitivity
            sensitivity = self._analyze_content_sensitivity(content)
            if sensitivity in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED]:
                if provider != AIProvider.LOCAL:
                    return False, f"Content sensitivity level {sensitivity.value} requires local processing only"
            
            # Check for blocked content types
            content_type = self._classify_content_type(content)
            if content_type in self.settings.blocked_content_types:
                return False, f"Content type {content_type} is blocked from AI processing"
            
            # Check if user approval is required
            if self.settings.require_approval:
                # In a real implementation, this would prompt the user
                # For now, we'll assume approval for non-sensitive content
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
            
            usage_log = AIUsageLog(
                content_hash=content_hash,
                provider=provider,
                task_type=task_type,
                timestamp=timestamp,
                data_sent_size=data_sent_size,
                anonymized=anonymized,
                user_approved=user_approved,
                retention_days=self.settings.max_retention_days
            )
            
            self.usage_log.append(usage_log)
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            expires_at = timestamp + timedelta(days=self.settings.max_retention_days)
            
            cursor.execute('''
                INSERT INTO ai_usage_log 
                (content_hash, provider, task_type, timestamp, data_sent_size, 
                 anonymized, user_approved, retention_days, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (content_hash, provider.value, task_type, timestamp, 
                  data_sent_size, anonymized, user_approved, 
                  self.settings.max_retention_days, expires_at))
            
            conn.commit()
            conn.close()
            
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
                # Replace sensitive patterns
                for i, pattern in enumerate(self.settings.sensitive_patterns):
                    matches = re.findall(pattern, anonymized_text)
                    for match in matches:
                        placeholder = f"[REDACTED_{i}]"
                        replacements[match] = placeholder
                        anonymized_text = anonymized_text.replace(match, placeholder)
                
                # Replace names (basic implementation)
                name_patterns = [
                    r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
                    r'\bMr\. [A-Z][a-z]+\b',         # Mr. Lastname
                    r'\bMs\. [A-Z][a-z]+\b',         # Ms. Lastname
                    r'\bDr\. [A-Z][a-z]+\b',         # Dr. Lastname
                ]
                
                for pattern in name_patterns:
                    matches = re.findall(pattern, anonymized_text)
                    for match in matches:
                        if match not in replacements:
                            placeholder = "[NAME]"
                            replacements[match] = placeholder
                            anonymized_text = anonymized_text.replace(match, placeholder)
            
            if anonymization_level == "aggressive":
                # Additional aggressive anonymization
                # Replace locations, organizations, etc.
                location_patterns = [
                    r'\b[A-Z][a-z]+ [A-Z][a-z]+ (Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b',
                    r'\b[A-Z][a-z]+, [A-Z]{2}\b',  # City, ST
                ]
                
                for pattern in location_patterns:
                    matches = re.findall(pattern, anonymized_text)
                    for match in matches:
                        if match not in replacements:
                            placeholder = "[LOCATION]"
                            replacements[match] = placeholder
                            anonymized_text = anonymized_text.replace(match, placeholder)
            
            logger.info(f"Content anonymized: {len(replacements)} replacements made")
            return anonymized_text, replacements
            
        except Exception as e:
            logger.error(f"Failed to anonymize content: {e}")
            return text, {}

    def get_privacy_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive privacy dashboard information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get usage statistics
            cursor.execute('''
                SELECT provider, COUNT(*), SUM(data_sent_size), 
                       AVG(anonymized), COUNT(CASE WHEN user_approved THEN 1 END)
                FROM ai_usage_log 
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY provider
            ''')
            
            usage_stats = []
            for row in cursor.fetchall():
                usage_stats.append({
                    'provider': row[0],
                    'requests': row[1],
                    'total_data_sent': row[2],
                    'anonymization_rate': row[3],
                    'approved_requests': row[4]
                })
            
            # Get data inventory summary
            cursor.execute('''
                SELECT sensitivity_level, COUNT(*), SUM(access_count)
                FROM data_inventory
                GROUP BY sensitivity_level
            ''')
            
            data_inventory = []
            for row in cursor.fetchall():
                data_inventory.append({
                    'sensitivity': row[0],
                    'items': row[1],
                    'total_accesses': row[2]
                })
            
            conn.close()
            
            dashboard_data = {
                'privacy_mode': self.privacy_mode.value,
                'settings': asdict(self.settings),
                'usage_statistics': usage_stats,
                'data_inventory': data_inventory,
                'recent_activity': self._get_recent_activity(),
                'privacy_score': self._calculate_privacy_score(),
                'recommendations': self._get_privacy_recommendations()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get privacy dashboard data: {e}")
            return {}

    def cleanup_expired_data(self) -> int:
        """Clean up expired data according to retention policies"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Remove expired AI usage logs
            cursor.execute('''
                DELETE FROM ai_usage_log 
                WHERE expires_at < datetime('now')
            ''')
            
            expired_logs = cursor.rowcount
            
            # Remove old data inventory entries (older than max retention)
            cursor.execute('''
                DELETE FROM data_inventory 
                WHERE created_at < datetime('now', '-' || ? || ' days')
            ''', (self.settings.max_retention_days,))
            
            expired_inventory = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            total_cleaned = expired_logs + expired_inventory
            logger.info(f"Cleaned up {total_cleaned} expired data records")
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0

    def export_privacy_data(self, format: str = "json") -> str:
        """Export user's privacy data for transparency/GDPR compliance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Export all privacy-related data
            cursor.execute('SELECT * FROM privacy_settings')
            settings_data = cursor.fetchall()
            
            cursor.execute('SELECT * FROM ai_usage_log')
            usage_data = cursor.fetchall()
            
            cursor.execute('SELECT * FROM data_inventory')
            inventory_data = cursor.fetchall()
            
            conn.close()
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'privacy_settings': settings_data,
                'ai_usage_log': usage_data,
                'data_inventory': inventory_data,
                'current_settings': asdict(self.settings)
            }
            
            if format.lower() == "json":
                return json.dumps(export_data, indent=2, default=str)
            else:
                # Could implement other formats (CSV, XML, etc.)
                return json.dumps(export_data, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to export privacy data: {e}")
            return "{}"

    def _analyze_content_sensitivity(self, content: str) -> DataSensitivity:
        """Analyze content to determine sensitivity level"""
        try:
            content_lower = content.lower()
            
            # Check for highly sensitive patterns
            sensitive_keywords = [
                'confidential', 'classified', 'secret', 'private',
                'medical', 'health', 'diagnosis', 'treatment',
                'financial', 'bank', 'account', 'salary', 'income',
                'legal', 'lawsuit', 'attorney', 'court'
            ]
            
            # Check for personal information patterns
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
                
        except Exception as e:
            logger.error(f"Failed to analyze content sensitivity: {e}")
            return DataSensitivity.CONFIDENTIAL  # Default to most restrictive

    def _classify_content_type(self, content: str) -> str:
        """Classify content into categories"""
        try:
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
                
        except Exception as e:
            logger.error(f"Failed to classify content type: {e}")
            return 'unknown'

    def _save_settings(self):
        """Save current settings to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            settings_json = json.dumps(asdict(self.settings), default=str)
            
            cursor.execute('''
                INSERT OR REPLACE INTO privacy_settings (id, mode, settings_json, updated_at)
                VALUES (1, ?, ?, datetime('now'))
            ''', (self.privacy_mode.value, settings_json))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _get_recent_activity(self) -> List[Dict]:
        """Get recent privacy-related activity"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT provider, task_type, timestamp, anonymized, user_approved
                FROM ai_usage_log
                WHERE timestamp >= datetime('now', '-7 days')
                ORDER BY timestamp DESC
                LIMIT 20
            ''')
            
            activity = []
            for row in cursor.fetchall():
                activity.append({
                    'provider': row[0],
                    'task_type': row[1],
                    'timestamp': row[2],
                    'anonymized': bool(row[3]),
                    'user_approved': bool(row[4])
                })
            
            conn.close()
            return activity
            
        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}")
            return []

    def _calculate_privacy_score(self) -> int:
        """Calculate a privacy score (0-100) based on current settings and usage"""
        try:
            score = 0
            
            # Base score from privacy mode
            if self.privacy_mode == PrivacyMode.PRIVATE:
                score += 40
            elif self.privacy_mode == PrivacyMode.SELECTIVE:
                score += 25
            else:
                score += 10
            
            # Score from settings
            if self.settings.auto_anonymize:
                score += 15
            if self.settings.require_approval:
                score += 15
            if len(self.settings.allowed_providers) == 1 and AIProvider.LOCAL in self.settings.allowed_providers:
                score += 15
            elif len(self.settings.allowed_providers) <= 2:
                score += 10
            
            # Score from retention policy
            if self.settings.max_retention_days <= 30:
                score += 10
            elif self.settings.max_retention_days <= 90:
                score += 5
            
            # Score from recent usage patterns
            recent_local_usage = len([log for log in self.usage_log[-50:] if log.provider == AIProvider.LOCAL])
            if recent_local_usage > 0:
                score += min(5, recent_local_usage)
            
            return min(100, score)
            
        except Exception as e:
            logger.error(f"Failed to calculate privacy score: {e}")
            return 50

    def _get_privacy_recommendations(self) -> List[str]:
        """Get personalized privacy recommendations"""
        recommendations = []
        
        try:
            if self.privacy_mode != PrivacyMode.PRIVATE:
                recommendations.append("Consider switching to Private mode for maximum privacy protection")
            
            if not self.settings.auto_anonymize:
                recommendations.append("Enable auto-anonymization to protect sensitive information")
            
            if self.settings.max_retention_days > 30:
                recommendations.append("Reduce data retention period to 30 days or less")
            
            if len(self.settings.allowed_providers) > 3:
                recommendations.append("Limit the number of allowed AI providers to reduce data exposure")
            
            # Check recent usage patterns
            external_usage = len([log for log in self.usage_log[-20:] if log.provider != AIProvider.LOCAL])
            if external_usage > 10:
                recommendations.append("High external AI usage detected - consider using local models more frequently")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return ["Enable privacy monitoring for personalized recommendations"]