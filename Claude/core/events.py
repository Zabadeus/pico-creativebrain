"""
Event system for inter-service communication.
"""
from typing import Any, Callable, Dict, List
import asyncio
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    """Types of events that can be published."""
    TRANSCRIPTION_STARTED = "transcription_started"
    TRANSCRIPTION_COMPLETED = "transcription_completed"
    TRANSCRIPTION_ERROR = "transcription_error"
    FILE_IMPORTED = "file_imported"
    SESSION_CREATED = "session_created"
    VERSION_CREATED = "version_created"
    PRIVACY_MODE_CHANGED = "privacy_mode_changed"
    AI_PROCESSING_STARTED = "ai_processing_started"
    AI_PROCESSING_COMPLETED = "ai_processing_completed"
    EXPORT_COMPLETED = "export_completed"
    SPEAKER_DETECTED = "speaker_detected"
    LIVE_RECORDING_STARTED = "live_recording_started"
    LIVE_RECORDING_STOPPED = "live_recording_stopped"

@dataclass
class Event:
    """Event data structure."""
    type: EventType
    data: Dict[str, Any]
    timestamp: float

class EventBus:
    """Event bus for publishing and subscribing to events."""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue = asyncio.Queue()
        self._running = False
        
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                
    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        await self._event_queue.put(event)
        
    async def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                event = await self._event_queue.get()
                if event.type in self._subscribers:
                    for callback in self._subscribers[event.type]:
                        try:
                            callback(event)
                        except Exception as e:
                            print(f"Error in event callback: {e}")
                self._event_queue.task_done()
            except Exception as e:
                print(f"Error processing event: {e}")
                
    async def start(self):
        """Start the event bus."""
        self._running = True
        asyncio.create_task(self._process_events())
        
    async def stop(self):
        """Stop the event bus."""
        self._running = False
        await self._event_queue.join()

# Global event bus instance
event_bus = EventBus()