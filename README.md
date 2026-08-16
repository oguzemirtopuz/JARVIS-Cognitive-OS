<div align="center">

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Asyncio Core](https://img.shields.io/badge/Architecture-Async_Orchestration-FF6F00?style=for-the-badge&logo=cpu&logoColor=white)](https://docs.python.org/3/library/asyncio.html)
[![Playwright](https://img.shields.io/badge/Playwright-Browser_Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![VectorDB Memory](https://img.shields.io/badge/Memory-ChromaDB_VectorDB-0052FF?style=for-the-badge&logo=databricks&logoColor=white)](https://www.trychroma.com/)
[![Google Gemini](https://img.shields.io/badge/AI-Gemini_2.5_Flash-8E75C2?style=for-the-badge&logo=google-gemini&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<h1>🧠 J.A.R.V.I.S. Cognitive OS</h1>
<h3>The AI that plans, executes, fails, and heals itself — without asking you for help.</h3>

<p><em>Not a chatbot. Not a wrapper. A self-directing cognitive agent architecture.</em></p>

</div>

---

## 🎯 What Problem Does This Solve?

Every AI assistant today has a fundamental flaw: **it stops the moment something goes wrong.**

API timeout? It crashes. Website structure changes? It freezes. Unexpected error? It asks you what to do.

J.A.R.V.I.S. was built to solve exactly this. It is a **Cognitive AI Operating System** — an autonomous agent that:
- Breaks down your high-level goals into executable plans
- Runs those plans using sandboxed browser, desktop, and file tools
- **Detects its own failures and rewrites its plan to work around them**
- Remembers every past success and failure in a local vector database
- Learns from patterns so it gets better at handling similar problems over time

**The era of "the AI crashed, now what?" is over.**

---

## 👥 Who This Is For

| Audience | Why JARVIS Matters |
|---|---|
| **AI/ML Engineers** | Study a production-grade LLM orchestration architecture with 39 specialized modules |
| **Automation Engineers** | Replace fragile RPA scripts with a self-healing agent that adapts to change |
| **Developers building agents** | Reference architecture for episodic memory, semantic routing, and dynamic skill synthesis |
| **Power users** | A local-first, privacy-respecting AI that controls your computer without cloud dependency |

---

## 🔥 The Hook: What Makes JARVIS Different

| Other AI Assistants | J.A.R.V.I.S. Cognitive OS |
|---|---|
| Crashes on errors | **Self-heals via Reflection Engine** |
| Stateless — forgets everything | **Episodic Vector Memory — recalls every past outcome** |
| Fixed tool set | **Dynamic Skill Synthesizer — writes new tools on the fly** |
| Always calls the LLM | **Semantic Router handles simple commands in milliseconds** |
| Generic chatbot interface | **Multi-input: Voice (Whisper STT), GUI, and CLI** |
| LLM-generated code runs unchecked | **AST Sandbox — un-bypassable security layer** |

---

## ⚡ Key Benefits

- **Zero hand-holding:** Set the goal. JARVIS figures out the path, the tools, and the recovery.
- **Privacy first:** All memory is stored locally in `memory_db/`. Nothing leaves your machine.
- **Speed-cost optimized:** The semantic router handles 80% of commands locally. The LLM is only called when cognition is actually needed.
- **Infinitely extensible:** Every new skill JARVIS synthesizes is permanently available for future tasks.
- **Windows-native:** Auto-start via `winreg`, desktop control via PyWinAuto, browser automation via Playwright.

---

## 🏛️ Technical Architecture

JARVIS is a non-blocking asynchronous system built on **39 specialized Python modules** organized into a layered cognitive architecture.

```
JARVIS Cognitive OS
│
├── Input Layer
│   ├── Voice (OpenAI Whisper STT)
│   ├── GUI (PyWebView interface)
│   └── CLI (text terminal with /slash commands)
│
├── Cognitive Core  
│   ├── brain.py           — Central orchestration hub
│   ├── planner.py         — Hierarchical PlanNode tree builder
│   ├── cognitive_core.py  — High-level goal decomposition
│   ├── execution_graph.py — Dependency-aware task graph
│   └── hypothesis_engine.py — Pre-execution failure prediction
│
├── Execution Layer
│   ├── engine.py          — Async orchestrator (main event loop)
│   ├── plan_executor.py   — Sequential/parallel plan runner
│   ├── executor.py        — Individual step executor
│   └── autonomous_loop.py — Continuous background operation
│
├── Tool Registry (Sandboxed)
│   ├── browser_tool.py    — Playwright web automation
│   ├── desktop_tool.py    — PyWinAuto desktop control
│   ├── file_tool.py       — File system operations
│   ├── system_tool.py     — OS-level operations
│   └── skill_synthesizer.py — Runtime tool generation via LLM + AST sandbox
│
├── Memory Subsystem
│   ├── memory.py          — Episodic + semantic storage
│   ├── memory_consolidator.py — LFU/LRU cache pruning
│   └── ChromaDB VectorDB  — Local embedding storage
│
└── Recovery & Reflection
    ├── reflection.py      — Failure analysis engine
    ├── reflector.py       — Plan rewrite generator
    └── recovery.py        — Execution resumption after healing
```

### 🧠 LLM Orchestration & Dynamic Tree Planning
The execution pipeline is not sequential — it is dynamic. High-level directives are parsed into a strict hierarchical tree of `PlanNode` objects. Complex tasks route to the LLM. Simple, recognized tasks route to the local **Semantic Router** in milliseconds — completely bypassing API calls for standard commands.

### 🪞 The Reflection Engine (Self-Healing System)
When a sub-task fails:
1. The async task queue is halted
2. Error logs and current environment state are analyzed autonomously
3. A **completely new sub-plan** is generated to bypass the obstacle
4. Execution resumes along the new path — zero human intervention required

### 💾 Cognitive Memory Subsystem
- **Episodic Recall:** Every success and failure is embedded into a local ChromaDB vector database. Similar future situations trigger automatic recall.
- **Self-Learning Router:** Learns from confirmed semantic matches. LFU/LRU pruning maintains efficiency over time.
- **Translation Cache:** A 700KB+ local Turkish-English term cache enables low-latency multilingual operations.

### ⚡ Dynamic Skill Synthesizer
When JARVIS encounters a tool requirement outside its registry:
1. It instructs the LLM to write a new async Python tool function
2. The generated code is validated through **AST security checks** — dunder attributes, `os.system`, `eval`, and `exec` are instantly blocked
3. The validated tool is hot-loaded into the registry
4. It remains available for all future tasks in that session

---

## ✨ Latest: v16.7.0 — Cognitive OS Systemic Hardening & Logical Bug Fixes
 
 > [!IMPORTANT]
 > **Key changes in v16.7.0:**
 > - **Cognitive OS Hardening:** Fixed 14 systemic logical bugs including parameter parsing edge-cases, audio concurrency race conditions, and EventBus wildcard double-dispatch.
 > - **Deterministic Telemetry & Memory Safety:** Guaranteed exception-resilient cognition loop telemetry and bounded cache eviction policies.
 > - **Exception Clean-Up:** Full removal of bare `except:` statements across all core subsystems for reliable system lifecycle management.

*(Full version history in [CHANGELOG.md](CHANGELOG.md))*

---

## 🔒 Security & Privacy

JARVIS operates under a **strict local-first security model:**

- **Local Memory:** All episodic data, vector embeddings, and semantic experience logs are stored in `memory_db/` — never transmitted externally
- **AST Sandbox:** Every LLM-generated Python tool is validated through an Abstract Syntax Tree inspector before execution. Critical attributes (`__class__`, `__globals__`, etc.) and system commands (`os.system`, `subprocess.call`) are hard-blocked.
- **Git Hygiene:** `.env` (API keys), `contacts.json`, and all local log/debug files are excluded from the public repository

---

## 🚀 Installation

### Requirements
- **Python 3.11** (recommended for optimal async performance)
- **FFmpeg** installed (required for OpenAI Whisper voice commands / Speech-to-Text)

### 📦 FFmpeg Installation
JARVIS requires `ffmpeg` to capture, convert, and decode voice inputs for the Whisper STT engine.

#### Option A: Windows (Automatic - Recommended)
Open **Command Prompt (CMD)** or **PowerShell** and run:
```bash
winget install Gyan.FFmpeg
```
*Note: Restart your terminal, CMD, or editor after the installation finishes to apply the system PATH changes.*

#### Option B: Windows (Manual - No System Settings Modified)
1. Download the essentials archive from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z).
2. Extract the archive, go to the `bin/` folder, and copy `ffmpeg.exe`, `ffplay.exe`, and `ffprobe.exe`.
3. Paste these `.exe` files directly into the root directory of this project (next to `main.py`).

#### Option C: macOS / Linux
Install via your system's package manager:
```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg
```

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/oguzemirtopuz/JARVIS-Cognitive-OS.git
cd JARVIS-Cognitive-OS
pip install -r requirements.txt
playwright install
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your-groq-api-key
GOOGLE_API_KEY=your-google-api-key
```
Get free API keys: [Groq Console](https://console.groq.com) · [Google AI Studio](https://aistudio.google.com)

### 3. Launch

| Mode | Command |
|---|---|
| Console Mode | `python main.py` |
| GUI Mode | `python launch_jarvis.pyw` |
| Windows Auto-Start | Run `install_startup.bat` |

---

## 🗺️ Roadmap

- [ ] Web dashboard for remote task monitoring
- [ ] Plugin marketplace for community-built tools
- [ ] Multi-agent collaboration (JARVIS spawning sub-agents)
- [ ] Mobile voice command integration
- [ ] Docker containerization for cross-platform deployment

---

## 🤝 Contributing

Contributions are welcome. Priority areas:

- New tool implementations (browser, desktop, API integrations)
- Additional semantic router training patterns
- Cross-platform support (macOS/Linux testing)
- New reflection strategy implementations

Please open an issue first to discuss significant changes.

---

## 🌌 Related Projects

- **[YouTube Analyse Pro](https://github.com/oguzemirtopuz/YouTube-Analyse-Pro-SaaS-Edition)** — AI-powered YouTube growth platform using the same async architecture principles
- **[PyAuditor](https://github.com/oguzemirtopuz/PyAuditor)** — The AST analysis toolkit used to audit JARVIS's own codebase

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built by <a href="https://github.com/oguzemirtopuz">Oğuz Emir Topuz</a></sub>
  <br/>
  <sub>⭐ If you believe in the future of autonomous systems, star this repository.</sub>
</div>
