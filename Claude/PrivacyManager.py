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
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path


class PrivacyMode(Enum):
    """Privacy operation modes"""
    PRIVATE = "private"          # No external AI calls, local processing only
    SELECTIVE = "selective"      # User-approved AI providers and tasks only
    OPEN = "open"               # All AI providers allowed for all tasks


class AIProvider(Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    HUGGINGFACE = "huggingface"
    OPENROUTER = "openrouter"
    LOCAL = "local"             # Local models only


class TaskType(Enum):
    """Types of AI tasks that require privacy consideration"""
    SUMMARIZATION = "summarization"
    CONTENT_CLEANING = "content_cleaning"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    SEARCH_ENHANCEMENT = "search_enhancement"
    CONTENT_GENERATION = "content_generation"
    TRANSLATION = "translation"
    SENTIMENT_ANALYSIS = "sentiment_analysis"


class SensitivityLevel(Enum):
    """Content sensitivity levels"""
    PUBLIC = "public"           # Safe to share with any provider
    INTERNAL = "internal"       # Company/personal content, limited sharing
    CONFIDENTIAL = "confidential"  # Sensitive content, local only
    RESTRICTED = "restricted"   # Highly sensitive, no AI processing


@dataclass
class AIUsageLog:
    """Log entry for AI usage tracking"""
    timestamp: datetime
    content_hash: str
    provider: AIProvider
    task_type: TaskType
    data_shared: Dict[str, Any]
    response_received: bool
    user_approved: bool
    sensitivity_level: SensitivityLevel
    anonymized: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderPermission:
    """Permission settings for an AI provider"""
    provider: AIProvider
    allowed: bool = False
    allowed_tasks: Set[TaskType] = field(default_factory=set)
    max_content_length: Optional[int] = None
    require_anonymization: bool = True
    auto_approve: bool = False
    usage_limit_daily: Optional[int] = None
    usage_count_today: int = 0
    last_used: Optional[datetime] = None


@dataclass
class ContentAnalysis:
    """Analysis of content for privacy considerations"""
    contains_pii: bool = False
    contains_sensitive_terms: bool = False
    sensitivity_level: SensitivityLevel = SensitivityLevel.PUBLIC
    detected_entities: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class PrivacyManager:
    """
    Comprehensive privacy management system for AI interactions.
    
    Features:
    - Multi-mode privacy controls (private/selective/open)
    - Granular AI provider permissions
    - Real-time usage logging and monitoring
    - Content analysis and anonymization
    - Compliance reporting and data retention
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.privacy_mode = PrivacyMode.SELECTIVE
        self.provider_permissions: Dict[AIProvider, ProviderPermission] = {}
        self.usage_log: List[AIUsageLog] = []
        self.config_path = config_path or "privacy_config.json"
        
        # Initialize default permissions
        self._initialize_default_permissions()
        
        # Privacy patterns for content analysis
        self._initialize_privacy_patterns()
        
        # Load existing configuration
        self.load_config()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _initialize_default_permissions(self):
        """Initialize default provider permissions"""
        for provider in AIProvider:
            self.provider_permissions[provider] = ProviderPermission(
                provider=provider,
                allowed=(provider == AIProvider.LOCAL),  # Only local allowed by default
                allowed_tasks=set(),
                require_anonymization=True,
                usage_limit_daily=100 if provider != AIProvider.LOCAL else None
            )
    
    def _initialize_privacy_patterns(self):
        """Initialize patterns for detecting sensitive content"""
        # PII detection patterns
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'url': r'https?://[^\s<>"{}|\\^`[\]]+',
        }
        
        # Sensitive term categories
        self.sensitive_terms = {
            'financial': ['bank account', 'credit score', 'salary', 'income', 'tax return'],
            'medical': ['medical record', 'diagnosis', 'prescription', 'patient', 'treatment'],
            'legal': ['legal document', 'contract', 'lawsuit', 'attorney', 'confidential'],
            'personal': ['password', 'private key', 'secret', 'confidential', 'proprietary'],
        }
    
    def set_privacy_mode(self, mode: PrivacyMode) -> None:
        """Set the overall privacy mode"""
        self.privacy_mode = mode
        self.logger.info(f"Privacy mode changed to: {mode.value}")
        
        # Adjust permissions based on mode
        if mode == PrivacyMode.PRIVATE:
            self._disable_all_external_providers()
        elif mode == PrivacyMode.OPEN:
            self._enable_all_providers()
        
        self.save_config()
    
    def configure_provider_permission(self, 
                                    provider: AIProvider, 
                                    allowed: bool = True,
                                    allowed_tasks: Optional[Set[TaskType]] = None,
                                    require_anonymization: bool = True,
                                    auto_approve: bool = False,
                                    daily_limit: Optional[int] = None) -> None:
        """Configure permissions for a specific AI provider"""
        
        if provider not in self.provider_permissions:
            self.provider_permissions[provider] = ProviderPermission(provider=provider)
        
        permission = self.provider_permissions[provider]
        permission.allowed = allowed
        permission.allowed_tasks = allowed_tasks or set()
        permission.require_anonymization = require_anonymization
        permission.auto_approve = auto_approve
        permission.usage_limit_daily = daily_limit
        
        self.logger.info(f"Updated permissions for {provider.value}: allowed={allowed}")
        self.save_config()
    
    def check_ai_permission(self, 
                           content: str, 
                           provider: AIProvider, 
                           task_type: TaskType,
                           auto_approve: bool = False) -> Tuple[bool, str, ContentAnalysis]:
        """
        Check if AI processing is permitted for given content and provider
        
        Args:
            content: Content to be processed
            provider: AI provider to use
            task_type: Type of task to perform
            auto_approve: Whether to auto-approve if permitted
            
        Returns:
            Tuple of (permission_granted, reason, content_analysis)
        """
        # Check privacy mode
        if self.privacy_mode == PrivacyMode.PRIVATE and provider != AIProvider.LOCAL:
            return False, "Privacy mode is set to PRIVATE - only local processing allowed", ContentAnalysis()
        
        # Analyze content for privacy considerations
        content_analysis = self.analyze_content(content)
        
        # Check if provider is configured and allowed
        if provider not in self.provider_permissions:
            return False, f"Provider {provider.value} not configured", content_analysis
        
        permission = self.provider_permissions[provider]
        
        if not permission.allowed:
            return False, f"Provider {provider.value} is not allowed", content_analysis
        
        # Check task permissions
        if permission.allowed_tasks and task_type not in permission.allowed_tasks:
            return False, f"Task type {task_type.value} not allowed for {provider.value}", content_analysis
        
        # Check daily usage limits
        if permission.usage_limit_daily:
            today = datetime.now().date()
            if permission.last_used and permission.last_used.date() != today:
                permission.usage_count_today = 0
            
            if permission.usage_count_today >= permission.usage_limit_daily:
                return False, f"Daily usage limit exceeded for {provider.value}", content_analysis
        
        # Check