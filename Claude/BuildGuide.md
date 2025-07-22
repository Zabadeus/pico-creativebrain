# PICO - AI Transcription & Second Brain App - Streamlined Build Guide

## 🎯 Project Vision

PICO (Processing Ideas Creating Output) - Cross-platform second-brain app for audio transcription with AI-powered content management and generation.

## 📊 Implementation Status (90% Backend Complete)

### ✅ FULLY IMPLEMENTED (Production Ready)

- **TranscriptionEngine.py**: faster-whisper + GPU acceleration + speaker diarization + word-level timestamps
- **UniversalInputHandler.py**: Live recording + YouTube/podcast processing + all audio formats
- **ContentVersionManager.py**: Original→Cleaned→Summary versions + multi-format export (JSON/SRT/VTT/TXT)
- **PrivacyManager.py**: GDPR-compliant privacy modes + PII detection + AI usage tracking
- **FileStorageManager.py**: Complete session lifecycle + file structure + knowledge management + session exports

### ❌ MISSING (Critical Path)

- **Flutter Frontend**: 0% complete - PRIMARY BLOCKER
- **AI Provider APIs**: Framework exists, need OpenAI/Claude/Gemini integrations
- **Knowledge Graph**: Database + semantic linking system
- **Testing Framework**: Unit/integration tests

## 🏗️ Architecture

### Data Flow

```
Audio Input → Whisper Transcription → Version Manager (Original/Cleaned/Summary) → AI Enhancement
     ↓                                       ↓                                    ↓
Privacy Check → Speaker Diarization → FileStorageManager (Sessions/Knowledge) → Export
                        ↓                         ↓
              Timestamp Preservation → Knowledge Linking (tags/insights/cross-refs)
```

### File Structure (Markdown-based - Managed by FileStorageManager)

```
transcripts/[session_id]/
├── metadata.json          # Session info, privacy settings, AI usage
├── audio/                 # original.wav + segments/ for timestamp mapping
├── versions/              # original.md, cleaned.md, summary.md
├── knowledge/             # tags.json, links.json, insights.md (AI-generated)
└── exports/               # Session packages (JSON/ZIP/HTML)
```

### Core Classes & Methods

```python
# TranscriptionEngine: transcribe(), get_speakers(), get_timestamps()
# UniversalInputHandler: process_file(), record_live(), download_youtube()
# ContentVersionManager: switch_version(), clean_text(), export_format()
# PrivacyManager: check_privacy(), log_ai_usage(), detect_pii()
# FileStorageManager: create_session(), load_session(), save_knowledge(), export_session()
```

### Export Functionality Split

- **ContentVersionManager**: Format exports (SRT/VTT/TXT/JSON) for individual transcripts
- **FileStorageManager**: Session exports (JSON/ZIP/HTML) for complete project packages

## 🚨 IMMEDIATE PRIORITIES

### 1. Flutter Frontend (CRITICAL - Weeks 1-2)

**Components Needed:**

- Main transcript view with version switching (Original/Cleaned/Summary)
- Media player with timestamp sync + click-to-jump
- File upload/URL input + live recording controls
- Multi-document tabs + side-by-side views
- Privacy dashboard + AI usage monitor
- Speaker management (rename Speaker 1→"Max", etc.)

**UI Specifications:**

- VSCode/Obsidian-style layout
- Left sidebar: File management + transcription + content creation + settings
- Header: Show/hide panels, search bar
- Multi-window support with synchronized highlighting
- Dark/light themes + customizable colors
- Context menu: Show original/cleaned/summary versions
- Drag-and-drop file upload

### 2. AI Integration (HIGH - Week 3)

**APIs to Connect:**

- OpenAI GPT-4 for content enhancement
- Claude for analysis/summarization
- Google Gemini for additional AI processing
- Local LLM support (llama.cpp)
- Connect to existing ContentVersionManager

### 3. Essential Features (Weeks 4-5)

- Bulk transcription processing
- Template system for automation workflows
- Cloud sync (Google Drive/OneDrive/iCloud)
- Calendar integration + timer/reminders
- Word count + analytics
- Speaker naming/management

## ⚙️ Technical Implementation Notes

### Flutter-Python Bridge

- Use `flutter_python` package or platform channels
- Python services run as background processes
- JSON communication for transcription data

### Privacy Implementation

- Three modes: PRIVATE (no AI), SELECTIVE (user approval), OPEN (full AI)
- Real-time PII scanning before AI processing
- Detailed usage logging with GDPR compliance

### Performance Optimizations

- GPU acceleration for Whisper (CUDA/MPS/CPU fallback)
- Chunked processing for large files
- Background transcription with progress callbacks
- Efficient timestamp indexing for instant seeking

### Export Formats

- Standard: TXT, SRT, VTT, JSON
- Custom: Markdown with metadata headers
- Integration-ready: Obsidian-compatible format

## 🎯 Success Metrics

- **Current Backend**: 90% complete (all core modules implemented)
- **Target Phase 1**: Flutter MVP with core transcription UI
- **Target Phase 2**: Full version management + AI integration
- **Target Phase 3**: Knowledge graph + advanced features

## 💡 Key Design Decisions

- Markdown-first storage for human readability + AI processing
- Privacy-by-design with granular controls
- Timestamp preservation across all content versions
- Modular architecture for easy feature additions
- Cross-platform compatibility (Windows/macOS/iOS/Web)
- Hybrid storage approach: filesystem for content, SQLite for indexing and relationships

## 🔄 Updated Architecture Design

### Technology Stack

**Frontend**: Flutter (recommended over Electron.js for better mobile support)

- Single codebase for iOS, Android, Windows, Mac, and web
- Can achieve VSCode/Obsidian-like interface with proper widget design
- Better mobile performance and app store compatibility

**Backend**: Python microservices

- Transcription, storage, privacy, input, knowledge, and AI services
- FastAPI for REST/HTTP communication with Flutter frontend
- WebSockets for real-time features

**Communication**:

- HTTP/REST API for most operations
- WebSockets for live transcription, progress updates, and real-time collaboration
- Platform channels for desktop-specific optimizations

### Data Storage Architecture

**Hybrid Approach**:

1. **Primary Storage**: Filesystem with Markdown files as the primary, authoritative source for transcript content, audio/video files, and session metadata
2. **Database as Index**: SQLite for metadata, relationships, tags, and full-text search data
3. **Synchronization**: Background service to keep database index updated with filesystem changes

**Data Storage Strategy**:

| Data Type              | Storage Method         | Reason                                      |
| ---------------------- | ---------------------- | ------------------------------------------- |
| **Transcript Content** | Filesystem (Markdown)  | Human-readable, Git-friendly, portable      |
| **Audio/Video Files**  | Filesystem             | Large binary files, direct playback         |
| **Session Metadata**   | Both (JSON + Database) | JSON for portability, database for querying |
| **Knowledge Graph**    | Database               | Complex relationships, fast queries         |
| **Tags & Categories**  | Database               | Fast filtering and search                   |
| **Cross-References**   | Database               | Relationship management                     |
| **Full-Text Search**   | Database (FTS)         | Fast text searching across all content      |
| **User Preferences**   | Database               | Structured data, fast access                |

### Microservices Architecture

The backend has been refactored into a modular microservices architecture to eliminate redundancies and improve maintainability:

```
pico_app/
├── core/
│   ├── __init__.py
│   ├── events.py                    # Event system for inter-service communication
│   ├── config.py                   # Centralized configuration
│   └── exceptions.py               # Custom exceptions
│
├── services/
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── engine.py               # Core transcription functionality
│   │   ├── diarization.py          # Speaker diarization
│   │   ├── speaker_manager.py      # Speaker definition and management
│   │   ├── bulk_processor.py       # Multi-file processing
│   │   └── models.py               # Model management and factory
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── file_manager.py         # File operations
│   │   ├── version_manager.py      # Version management
│   │   ├── export_service.py       # Export functionality
│   │   └── cloud_sync.py           # Google Drive, OneDrive, iCloud
│   │
│   ├── privacy/
│   │   ├── __init__.py
│   │   ├── manager.py              # Privacy logic
│   │   ├── database.py             # Database operations
│   │   └── policies.py             # Privacy policies and rules
│   │
│   ├── input/
│   │   ├── __init__.py
│   │   ├── handler.py              # Input handling interface
│   │   ├── youtube.py              # YouTube-specific handling
│   │   ├── podcast.py              # Podcast-specific handling
│   │   ├── local_file.py           # Local file handling
│   │   └── live_recording.py       # Live recording handling
│   │
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── graph.py                # Knowledge graph implementation
│   │   ├── linking.py              # Semantic linking system
│   │   ├── templates.py            # Automation templates
│   │   └── calendar.py             # Calendar and project planning
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── agent_manager.py        # AI agent management
│   │   ├── chat_terminal.py        # AI chat interface
│   │   ├── context_analyzer.py     # Cross-version text analysis
│   │   └── api_handler.py          # API key management
│   │
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py          # Main application window
│       ├── sidebar.py              # Left sidebar components
│       ├── header.py               # Header components
│       ├── tabs.py                 # Tab management
│       ├── multi_view.py           # Multi-window/section views
│       └── themes.py               # Theme management (dark/light)
│
├── models/
│   ├── __init__.py
│   ├── data_models.py              # Shared data models
│   ├── enums.py                    # Shared enums
│   └── ui_models.py                # UI-specific models
│
├── utils/
│   ├── __init__.py
│   ├── audio.py                    # Audio utilities
│   ├── file.py                     # File utilities
│   ├── temp_manager.py             # Temporary file management
│   ├── logger.py                   # Centralized logging
│   └── timer.py                    # Timer and reminder utilities
│
├── web/
│   ├── __init__.py
│   ├── server.py                   # Web server for Electron integration
│   └── api.py                      # REST API endpoints
│
└── main.py                         # Application entry point
```

### Code Optimization and Redundancy Removal

The following redundancies have been addressed in the refactored architecture:

1. **FileStorageManager.py and ContentVersionManager.py Redundancy**:

   - Separated concerns: FileStorageManager handles only file operations while ContentVersionManager handles version management
   - Eliminated duplicate code for version export functionality
   - Removed duplicate ContentVersion dataclass definition

2. **PrivacyManager.py Improvements**:

   - Separated business logic from data persistence
   - Simplified database schema
   - Made privacy policies more flexible and configurable

3. **UniversalInputHandler.py Refactoring**:

   - Split into dedicated modules for each input type (YouTube, podcast, local file, live recording)
   - Standardized error handling across input types
   - Centralized temporary file management

4. **TranscriptionEngine.py Enhancements**:
   - Separated speaker diarization into its own service
   - Split live streaming functionality into a dedicated module
   - Extended factory pattern for more configuration options

### Implementation Plan

1. **Phase 1: Backend Refactoring**

   - [ ] Create microservices directory structure
   - [ ] Refactor existing code into services
   - [ ] Implement event system for inter-service communication
   - [ ] Create shared models and utilities
   - [ ] Update main application to use new architecture

2. **Phase 2: Flutter Frontend Development**

   - [ ] Set up Flutter project with proper directory structure
   - [ ] Implement core UI components (sidebar, header, main area)
   - [ ] Create transcript viewer with version switching
   - [ ] Implement media player with timestamp synchronization
   - [ ] Add file upload and recording controls

3. **Phase 3: Flutter-Python Integration**

   - [ ] Set up FastAPI server for Python backend
   - [ ] Implement HTTP/REST API endpoints
   - [ ] Add WebSocket support for real-time features
   - [ ] Create platform channels for desktop-specific features

4. **Phase 4: Enhanced Features**

   - [ ] Implement knowledge graph with SQLite database
   - [ ] Add template system for automation workflows
   - [ ] Develop AI agent management system
   - [ ] Implement cloud sync with Google Drive, OneDrive, and iCloud
   - [ ] Add calendar and project planning features

5. **Phase 5: Testing and Optimization**
   - [ ] Create comprehensive test suite
   - [ ] Optimize performance across all platforms
   - [ ] Conduct user testing and gather feedback
   - [ ] Prepare for app store submissions

---

**Next Action**: Begin backend refactoring to implement microservices architecture
