# VAANIWEB — Vernacular Voice-First Autonomous Web Navigator

> **"Your Voice. Your Language. Your Web."**

VaaniWeb is a vernacular voice-driven autonomous browser agent prototype that enables users to operate websites primarily available in English through natural voice commands in their preferred regional language.

Supported Languages:
- **Kannada (ಕನ್ನಡ)**
- **Hindi (हिन्दी)**
- **Tamil (தமிழ்)**
- **English**

---

## 1. Project Architecture

```
User Voice / Text Command (Kannada / Hindi / Tamil / English)
       │
       ▼
[ Vernacular Voice Assistant Orb ] (Push-to-Talk / Web Speech / ElevenLabs)
       │
       ▼
[ FastAPI Backend + WebSockets ] (Real-time duplex event streaming)
       │
       ├─► [ AWS Bedrock LLM Engine ] (With labeled deterministic reasoning fallback)
       ├─► [ User Profile & Translation MCP Server ] (Python MCP SDK)
       │
       ▼
[ Autonomous Navigator Agent ]
       │
       ▼
[ Playwright MCP & Accessibility Inspection ]
       │
       ├─► Inspects Accessibility Tree (`aria_snapshot`, CDP AX Tree)
       ├─► Identifies Semantic Elements (Buttons, Inputs, Selects, Roles)
       ├─► Interacts: Navigation, Typed Filling, Dropdown Selection, Clicking
       │
       ▼
[ Confirm-Before-Commit Safety Guardrail ]
       │
       ├─► Intercepts Sensitive Actions (Booking commitment, payments, OTPs)
       ├─► Pauses Playwright execution & issues verification token
       ├─► Prompts user via Vernacular Spoken Warning & UI Approval Card
       │
       ▼ (On User Approval)
[ Commits Booking & Extracts Confirmation ] (PNR, Seat, Berth, QR details)
       │
       ▼
[ Live Browser Panel & Action Audit Log ] (Real-time screenshots & audio narration)
```

---

## 2. Technology Stack

- **Frontend**:
  - React 18, Vite 6, HTML5, CSS3 with Glassmorphic Dark Futuristic Theme
  - Lucide React Icons
  - Real-time WebSocket duplex client
  - Web Speech API integration for speech recognition & text-to-speech fallback
- **Backend**:
  - Python 3.11, FastAPI, Starlette WebSockets, Uvicorn
  - Pydantic v2 Settings & Models
- **AI / Intent Planning**:
  - **AWS Bedrock LLM** (supports Claude 3.5 Sonnet / Haiku / Amazon Nova)
  - **Deterministic Vernacular Reasoning Fallback**: Automatically and transparently active when AWS credentials are not configured in `.env`, clearly labeled as `engine: "bedrock_fallback"` (never falsely claimed).
- **Browser Automation**:
  - Official Playwright MCP Server architecture (`@playwright/mcp`) & Python Async Playwright
  - Real accessibility tree snapshot inspection (`page.aria_snapshot()`)
  - Semantic element identification (ARIA roles, accessible labels, placeholders)
  - Real-time base64 screenshot streaming to the frontend
- **Voice Integration**:
  - **ElevenLabs API** (`eleven_multilingual_v2` model for regional Kannada, Hindi, Tamil, English TTS)
  - **Browser Web Speech API Fallback**: When ElevenLabs API key is absent, the app automatically switches to the browser's speech synthesis and recognition engines with regional voices (`kn-IN`, `hi-IN`, `ta-IN`, `en-IN`), accompanied by text input fallback.
- **Model Context Protocol (MCP)**:
  - Custom User Profile & Translation Server built with the official Python MCP SDK (`mcp.server.mcpserver.MCPServer`)
  - Provides session preference management, vernacular railway station standardizer, travel class standardizer, and relative date resolver.
- **Safety**:
  - Backend-enforced **Confirm-Before-Commit** guardrail engine that halts automation before irreversible financial or booking commitments.
- **Demonstration Portal**:
  - Fully functional local railway reservation portal (`BharatRail Express`) served on `/portal/` with accessible ARIA elements and simulated booking confirmation.

---

## 3. Directory Structure

```
VaaniWeb/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx             # Top bar with real-time engine badges
│   │   │   ├── LiveBrowserPanel.jsx   # Live viewport screenshot & URL bar
│   │   │   ├── VoiceAssistantOrb.jsx  # Animated 3D pulsing voice orb & language tabs
│   │   │   └── ActionAuditLog.jsx     # Step progress, confirm card, action timeline
│   │   ├── pages/
│   │   │   └── Dashboard.jsx          # Main 3-panel dashboard layout
│   │   ├── services/
│   │   │   └── api.js                 # REST client & WebSocket manager
│   │   ├── styles/
│   │   │   └── index.css              # Dark futuristic glassmorphic styling
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint, WebSockets & static mount
│   │   ├── api/
│   │   │   ├── routes.py              # REST API endpoints (/api/command, /api/confirm, etc.)
│   │   │   └── websocket_manager.py   # WebSocket broadcast connection manager
│   │   ├── agent/
│   │   │   └── navigator_agent.py     # Autonomous agent orchestrator
│   │   ├── browser/
│   │   │   ├── browser_controller.py  # Playwright controller & screenshot capture
│   │   │   └── playwright_mcp_bridge.py # Playwright MCP tool interface
│   │   ├── services/
│   │   │   ├── bedrock_service.py     # AWS Bedrock + deterministic fallback engine
│   │   │   └── elevenlabs_service.py  # ElevenLabs TTS & STT client
│   │   ├── safety/
│   │   │   └── guardrail.py           # Confirm-Before-Commit safety engine
│   │   ├── mcp/
│   │   │   └── user_profile_server.py # Python MCP SDK User Profile & Translation server
│   │   ├── models/
│   │   │   └── schemas.py             # Pydantic models for actions, plans, logs
│   │   └── core/
│   │       └── config.py              # Settings loaded from .env
│   ├── mock_portal/
│   │   └── index.html                 # BharatRail Accessible Railway Booking Simulation
│   ├── tests/
│   │   ├── test_browser.py            # Playwright inspection and fill tests
│   │   ├── test_api.py                # FastAPI routes and status tests
│   │   └── test_agent_workflow.py     # End-to-end autonomous navigation & guardrail tests
│   ├── requirements.txt
│   └── .env.example
│
├── README.md
└── .gitignore
```

---

## 4. Setup and Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Google Chrome / Chromium (installed automatically by Playwright)

### Step 1: Backend Setup
```bash
# Navigate to the workspace root
cd /Users/dhanushbk/Desktop/VaaniWeb

# Create virtual environment if not already created
uv venv .venv --python /usr/local/bin/python3.11
# Or: python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install backend dependencies
uv pip install --python .venv/bin/python -r backend/requirements.txt

# Install Playwright Chromium browser
.venv/bin/playwright install chromium
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `backend/.env`:
```bash
cp backend/.env.example backend/.env
```

If you have AWS Bedrock or ElevenLabs credentials, add them to `backend/.env`:
```ini
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

> **Note:** If credentials are not provided, VaaniWeb automatically switches to the built-in deterministic vernacular intent engine and browser speech synthesis, with all features fully functional.

### Step 3: Frontend Setup
```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 5. Running the Application

Open two terminal tabs:

### Terminal 1: Start Backend (FastAPI + WebSocket + Playwright)
```bash
cd /Users/dhanushbk/Desktop/VaaniWeb
source .venv/bin/activate
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Documentation: `http://127.0.0.1:8000/docs`
- Demonstration Railway Portal: `http://127.0.0.1:8000/portal/`

### Terminal 2: Start Frontend (React + Vite)
```bash
cd /Users/dhanushbk/Desktop/VaaniWeb/frontend
npm run dev
```
- Open browser at `http://127.0.0.1:5173`

---

## 6. How to Test the Vernacular Railway Demonstration

1. Open `http://127.0.0.1:5173` in your browser.
2. The **Live Browser Panel** will show the real Playwright-controlled viewport showing BharatRail Express.
3. Select your language from the top tabs (e.g., **ಕನ್ನಡ**, **हिन्दी**, **தமிழ்**, or **English**).
4. Click the **Quick Suggestion Chip** or speak into the microphone orb or type:
   - **Kannada**: `ಬೆಂಗಳೂರು ಇಂದ ಮೈಸೂರಿಗೆ ನಾಳೆ ರೈಲು ಹುಡುಕಿ`
   - **Hindi**: `बेंगलुरु से मैसूर कल की ट्रेन खोजें`
   - **Tamil**: `பெங்களூரிலிருந்து மைசூருக்கு நாளை ரயில் தேடுங்கள்`
   - **English**: `Find a sleeper train from Bengaluru to Mysuru tomorrow morning`
5. Watch the autonomous agent in action:
   - Accessibility tree is inspected.
   - Departure and destination stations are populated.
   - Travel date is set to tomorrow.
   - Sleeper class is selected.
   - "Search Trains" button is clicked.
   - Real-time screenshot updates in the **Live Browser Panel**.
   - Available trains (e.g. Wodeyar Express) are parsed and selected.
   - Primary passenger details are entered.
6. **Safety Guardrail in Action**:
   - The agent reaches the final ticket booking commitment button.
   - Execution pauses instantly.
   - Spoken audio warning prompts the user in their language.
   - An amber **CONFIRM-BEFORE-COMMIT REQUIRED** card appears in the Action Audit Log.
7. Click **"Approve & Book"**:
   - The agent resumes execution and completes the simulated booking.
   - Confirmed PNR (e.g. `PNR: 452-9182736`), coach, berth, and QR details appear in the viewport.
   - The agent speaks the final confirmation summary.
8. Test **Cancel Action**:
   - Run the command again. When the confirmation prompt appears, click **"Cancel"**.
   - Notice the agent immediately aborts without booking.
9. Test **Emergency Stop**:
   - During execution, click the red **"Stop Task"** button to halt automation at any time.

---

## 7. Running Automated Tests

All tests can be executed with a single command:
```bash
cd /Users/dhanushbk/Desktop/VaaniWeb
PYTHONPATH=. .venv/bin/pytest backend/tests/ -v
```

Tests verified:
1. `backend/tests/test_browser.py`:
   - Playwright browser startup in Chromium
   - Accessibility snapshot (`aria_snapshot`) extraction
   - Semantic element evaluation
   - Playwright MCP tool dispatch (`browser_fill_element`, `browser_click`)
   - Real screenshot capture
2. `backend/tests/test_api.py`:
   - FastAPI server startup and `/api/status` inspection
   - Static mounting of the accessible demonstration portal
3. `backend/tests/test_agent_workflow.py`:
   - End-to-end autonomous navigation in Kannada
   - Confirm-Before-Commit interception of financial action
   - Simulated booking completion on user approval
   - Verification of safety cancellation behavior when user rejects
