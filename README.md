# UNISEBA
### *The AI layer that reads your screen so you don't have to.*

![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge)
![OCR](https://img.shields.io/badge/OCR-EasyOCR-1f6feb?style=for-the-badge)
![AI](https://img.shields.io/badge/AI-Groq%20LLaMA-f59e0b?style=for-the-badge)

<hr />

## The Problem
Every AI workflow still asks you to copy and paste.  
But the text you need often lives where copy-paste fails: images, remote desktops, legacy tools, scanned docs.  
That friction breaks focus exactly when you need speed.

<hr />

## What Uniseba Does
**Uniseba** turns your live screen into a searchable, explainable layer.  
You see text. You search it. You understand it. Without touching the source app.

<hr />

## Core Features

| Feature | What makes it special |
|---|---|
| ⚡ **Instant Search** | Search any visible text across almost any Windows app and get live on-screen highlights in context. |
| 🧠 **AI Summarize** | Record while you scroll, then generate a concise summary from the captured session corpus. |
| 🔗 **Knowledge Graph** | Convert captured screen content into a relationship graph you can explore visually in a dedicated window. |

<hr />

## How It Works
1. Press `Ctrl+Shift+U`.
2. Uniseba captures your target window and extracts text via **EasyOCR**.
3. **Fuzzy search** runs instantly on the live OCR index.
4. Record mode accumulates phrases as you scroll.
5. One click sends context to **Groq LLaMA** for summary or graph generation.

<hr />

## Demo
**[Screenshot/GIF coming soon]**

<hr />

## Tech Stack

| Layer | Technology |
|---|---|
| OCR | EasyOCR, Pillow, NumPy |
| Search | RapidFuzz + optional sentence-transformers reranking |
| AI | Groq API (`llama-3.3-70b-versatile`) |
| Graph | vis.js rendered in pywebview |
| UI | customtkinter + tkinter overlay/panels |
| Platform | Windows (Win32 APIs, keyboard hooks, tray integration) |

<hr />

## Getting Started

```bash
git clone <your-repo-url>
cd uniseba
```

```powershell
python -m venv venv311
.\venv311\Scripts\Activate.ps1
pip install -r requirements.txt
pip install groq python-dotenv pywebview
```

Create a `.env` file in project root:

```env
GROQ_API_KEY=your_key_here
```

Run:

```powershell
python main.py
```

<hr />

## Architecture In One Paragraph
Uniseba runs a **three-thread architecture**: the **main UI thread** handles interaction and drawing, an **OCR worker thread** continuously captures and indexes visible text, and a **semantic worker thread** performs optional reranking. These threads communicate through queue-based messaging (`index_queue`, `semantic_request_queue`, `semantic_result_queue`), which keeps heavy OCR and AI work off the UI loop so the interface stays responsive under real-time updates.

<hr />

## What Makes It Different
- Works on text you cannot normally copy: images, VMs, remote sessions, legacy software.
- Treats the **screen itself** as input, not the app beneath it.
- Blends local OCR speed with cloud AI reasoning in one seamless flow.

<hr />

## Latest Benchmarks (Apr 4, 2026)

| Metric | Result |
|---|---|
| OCR cycle latency (`total_cycle_ms`) | n=143, mean 2009.79 ms, p50 1413.00 ms, p90 4581.00 ms |
| Search latency (`total_search_ms`) | n=179, mean 4.73 ms, p50 3.90 ms, p90 8.50 ms |
| Semantic merge (`merge_ms`) | n=179, mean 0.07 ms, p90 0.10 ms |
| Controlled query benchmark | hit@1 20/20, hit@5 20/20, hit@10 20/20 on `test_crop.png` |

Benchmark notes:
- Runtime metrics are extracted from `uniseba.log` for `2026-04-04`.
- Accuracy benchmark is currently single-scene and should be expanded for broader validity.

<hr />

Built with obsession over latency, accuracy, and the belief that your screen should be as searchable as the internet.
