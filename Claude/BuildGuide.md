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

---

**Next Action**: Begin Flutter frontend development - backend is ready to support full-featured UI.
