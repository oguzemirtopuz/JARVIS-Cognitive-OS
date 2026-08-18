# Changelog

All notable changes to **J.A.R.V.I.S. Cognitive OS** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v16.7.1] - 2026-08-18
### Fixed
- **[Audio/STT] Reasoning Tag Sanitization:** Added automatic `<think>...</think>` block stripping in Groq and Gemini transcription polishers (`_polish_with_groq`, `_polish_with_gemini`), preventing internal model monologues from polluting voice command inputs.

---

## [v16.7.0] - 2026-08-16
### Fixed
- **[System/Tools] Parameter Parsing Order (`BUG #1`):** Fixed a critical `AttributeError` in `LLMEvalTool` and `YouTubeStrategyTool` where `.get()` was invoked before `isinstance(params, str)` type checking.
- **[Core/Cognition] Telemetry State Reliability (`BUG #2`):** Removed fragile `'situation' in dir()` lookup in `core/autonomous_loop.py`, guaranteeing deterministic cycle telemetry logging even across exception handlers.
- **[Learner] Turkish Stemming Regex Suffixes (`BUG #3`):** Added missing dotless `ı` and eliminated false-positive `y` stripping in `core/adaptive_learner.py` Turkish morphology stemmer (`[yiiuü]` → `[ıiuü]`).
- **[Audio/TTS] Singleton Race Condition & Cache Eviction (`BUG #4`, `#7`, `#14`):**
  - Integrated `threading.Lock` across concurrent TTS threads sharing the singleton `pygame.mixer.music` channel to prevent playback cut-offs and state collisions.
  - Guarded `pygame.mixer.music.unload()` with a loaded verification flag to prevent unloading non-existent audio handles.
  - Implemented bounded eviction for `_TRANSLATION_CACHE` (capped at 500 entries) preventing long-term memory leaks.
- **[Core/EventBus] Wildcard Double-Dispatch & Error Propagation (`BUG #5`, `#6`, `#10`, `#11`):**
  - Resolved double event triggering on wildcard dispatch (`emit("*")`).
  - Added exception inspection on `asyncio.gather` tasks to prevent subscriber errors from being silently discarded.
  - Converted history storage from list to `collections.deque(maxlen=100)` for $O(1)$ amortized memory operations.
- **[Core/Executor] Timeout Telemetry & Context Immutability (`BUG #8`, `#9`):**
  - Ensured all tool timeout instances trigger `telemetry.log_tool_execution()`.
  - Enforced read-only engine context guarantees by shallow-copying `engine_context` before injecting internal references.
- **[Security/Stability] Exception Hygiene (`BUG #12`):** Replaced bare `except:` clauses with explicit `except Exception:` across 7 modules (`contact_manager.py`, `goals.py`, `plan_executor.py`, `vision.py`, `analiz_pro_tool.py`, `native_ops.py`, `tts.py`), ensuring system signals (`KeyboardInterrupt`, `SystemExit`) are never intercepted.
- **[Tools/Browser] Async State Lock (`BUG #13`):** Added asynchronous lock guards around module-level URL state in `tools/browser_tool.py`.

---

## [v16.6.0] - 2026-08-14
### Changed
- **[Core/Brain] Groq Model Migration:** Migrated deprecated Groq LLMs (`llama-3.3-70b-versatile`, `llama-3.1-70b-versatile`, `llama-3.1-8b-instant`) to production-ready open-weight alternatives:
  - Primary Brain & Reflection Engine: Upgraded to `qwen/qwen3.6-27b` providing high throughput (250K TPM on Groq Free Tier), 131K context window, native reasoning traces, and structured tool calling.
  - Fast Fallback & Translator: Upgraded to `openai/gpt-oss-20b` for low-latency Turkish translations in `io_bridge.py` and secondary fallback in `core/config.py`.
- **[STT] Audio Polisher Migration:** Updated Groq-based audio transcript polisher in `audio/stt.py` to use `qwen/qwen3.6-27b`.
- **[Brain] Dynamic History Trimming:** Adapted token-limit history pruning inside `core/brain.py` to target compact 20B models to avoid rate limit breaches on free tiers.

### Added
- **[Planner/Reflection] Multi-Action Goal Decomposition:** Enhanced prompt constraints in `core/planner.py` to automatically split compound user instructions (separated by commas, 've', 'ardından', 'sonra') into sequential DAG nodes.
- **[Native Ops] Desktop Application Aliases:** Extended Turkish alias mappings in `tools/utils/native_ops.py` for Calculator (`hesap makinesi`), Notepad (`not defteri`), File Explorer (`dosya gezgini`), CMD (`komut istemi`), and Windows Settings (`ayarlar`).

---

## [v16.5.1] - 2026-06-03
### Added
- **[System/UI] Dual-Engine Logging & TTS:** Implemented a new intelligent translation layer inside `io_bridge.py`. When the UI language is set to Turkish, J.A.R.V.I.S. continues to use English for its Text-To-Speech (TTS) engine to avoid accent distortions, but dynamically translates its spoken text into Turkish for the UI LOG panel using either a rapid static dictionary or an asynchronous LLM call.

---

## [v16.5.0] - 2026-06-02
### Added
- **[UI/System] Settings Module & Auto-Start:** Integrated a dedicated SETTINGS tab into the HUD. Features include dynamic Screen Analysis Interval selection, one-click Windows Auto-Start registration (`winreg`), and a synchronized Language Switcher.
- **[System] Dynamic Screen Analysis:** Upgraded the `ProactiveWatcher` to accept user-defined intervals directly from the new Settings Module. Automatically pauses operations when disabled, saving API tokens.
- **[Commands] Slash Shortcuts:** Added direct slash commands (`/analysis 5`, `/analiz kapat`, etc.) to instantly control the watcher interval from the text interface.

### Fixed
- **[Core] Google GenAI Migration:** Upgraded the legacy `google.generativeai` imports to the new `google.genai` SDK and adapted prompting logic for the `gemini-2.5-flash` model inside `audio/stt.py`.
- **[UI] Scrollbar Aesthetics:** Replaced legacy TKinter scrollbars with elegant `ctk.CTkScrollbar` components matching the J.A.R.V.I.S. dark blue theme.
- **[Stability] State Transition Logic:** Patched an invalid state transition warning in `core/state_manager.py` that occurred when a task tried transitioning to its already active state.

---

## [v16.4.0] - 2026-05-30
### Added
- **[System] Bilingual Input Core:** J.A.R.V.I.S. now seamlessly understands and processes both English and Turkish voice commands regardless of the active UI mode. TTS responses are strictly enforced in English to prevent audio distortion.
- **[Core] Autonomous Bug Squashing:** Added extensive Turkish language detection in system logging loops for proper user/jarvis text color tagging on the HUD.

### Fixed
- **[Stability] Brain Asyncio Race Condition:** Fixed a critical flaw where `_lock` lazy-loading allowed two threads to override the LLM execution lock, breaking mutual exclusion.
- **[Stability] Event Loop Blocking:** Moved `locale.setlocale` out of the asynchronous `think()` block to prevent synchronous event loop freezing.
- **[UI] GUI State & Layout:** Restored invisible scrollbars in the Log panel, patched memory counters that failed to translate dynamically, and fixed `TEXT MODE` detection logic.
- **[Watcher] Dead Code:** Cleaned up unused `JarvisVision` initializations and dead interval parameters from the `ProactiveWatcher`.

---

## [v16.3.0] - 2026-05-30
### Added
- **[System] STT Initialization Logs:** Translated the Groq Whisper & Fallback Google Web Speech API initialization logs to English to ensure a fully unified English system/console experience.
- **[UI/System] Global Translation:** Translated all major UI elements (HAFIZA to MEMORY, YAZILI MOD to TEXT MODE, KAPATILIYOR to SHUTTING DOWN), system logs, comments, and debug messages to English across the core system.

### Fixed
- **[Stability] Proactive Watcher Idle Fix:** Fixed a critical bug where the Proactive Watcher would mistakenly assume the user wanted to shut down J.A.R.V.I.S. after exactly 15 minutes of inactivity. Added a strict calibration rule forbidding the `SYSTEM_SHUTDOWN` and `SYSTEM_POWER` protocols during background proactive cycles.
- **[Core] System Tool Restoration:** Restored `system_tool.py` ensuring that all tool classes (StressTestTool through YouTubeStrategyTool) are fully operational.

---

## [v16.2.0]
### Added
- **[Installer] 1-Click System Setup (`install.bat`):** Added a new, fully automated 7-step installer for Windows systems. Sets up Python `venv`, fetches FFmpeg, manages configs, and places a desktop shortcut.

### Fixed
- **[Optimizations] Memory Leak Fix:** Addressed a critical memory leak in `SemanticRouter` during TF-IDF vector pruning.
- **[Optimizations] Semantic Routing Threshold:** Expanded confidence routing; scores between `0.30 <= score < 0.65` now match with `is_forced=False`, keeping local matching speed while leaving final validation to the cognitive LLM.

---

## [v16.1.0] - The Architect Update
### Added
- **[Security] Un-bypassable AST Sandbox:** Enhanced AST validation of `DynamicSkillSynthesizer` to block all potential sandbox escape vectors. Direct built-in manipulation (`__import__`, `getattr`, `setattr`, `globals`, `locals`, `compile`) and dunder attributes (`__builtins__`, `__dict__`, `__class__`, etc.) are now strictly blocked. Validation runs entirely asynchronous in a thread pool to avoid blocking the event loop.
- **Async LRU & FFmpeg Integration:** Refactored caching to support async flows and integrated FFmpeg properly for local audio operations.
- **Code Freeze:** Formalized core OS stability with strict checks and silent exception swallowing prevention.

---

## [v16.0.0]
### Added
- **[Dynamic Skill Synthesizer]:** Autonomously writes its own asynchronous Python tools on the fly, applies AST security checks, and hot-loads them into the registry.

---

## [v15.4.0]
### Added
- **[Cognitive OS Evolution]:** TTS cache, sandbox input block, reflection self-healing engine, and dynamic config updates.
- **[Memory Protocols]:** Added `REMEMBER` and `STARTUP_REMINDER` protocols for true episodic memory creation.

---

## [v15.0.0]
### Added
- **[Self-Learning Loop]:** Implemented autonomous self-learning loop with dynamic embedding cache.
- **[Semantic Router]:** Implemented zero-latency vector-based semantic router, replacing the legacy regex engine.

---

## [v13.2.0]
### Added
- **[Ghost Shield]:** Implemented Ghost Shield to prevent Whisper hallucinations and low-energy speech processing.
- **[Updater]:** Added one-click auto-updater (`update.py`) — no Git required, protects personal data.

---

*(Earlier version histories can be found within the repository commit history.)*
