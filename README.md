# Agentic AI Chat (Gradio)

This repository contains a simple **agentic AI** chat application built with [Gradio](https://gradio.app/) and the [OpenAI Python SDK](https://github.com/openai/openai-python). It supports tools like PDF reading and push notifications via Pushover.

## Features

- Chat UI with Gradio (`gr.ChatInterface`).
- Uses the **OpenAI** client (`from openai import OpenAI`) to stream and handle tool calls.
- Tooling includes:
  - **PDF ingestion** via `pypdf.PdfReader`.
  - **Push notifications** using the **Pushover** REST API (optional).
- Environment configuration with **python-dotenv**.
- Example notebook: `4_lab4.ipynb`.

## Project structure

```
.
├── app.py               # Main Gradio app
├── requirements.txt     # Python dependencies
├── .env.example         # Template for environment variables
└── .gitignore           # Git ignore rules
```

## Getting started

### 1) Clone and set up a virtual environment
```bash
git clone <your-repo-url>.git agentic-ai-app
cd agentic-ai-app

# create a virtual env (choose one)
python -m venv .venv && source .venv/bin/activate   # macOS/Linux
# or
py -m venv .venv && .venv\Scripts\activate        # Windows (PowerShell)
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure environment variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env   # macOS/Linux
# or manually create .env on Windows
```

Required:
- `OPENAI_API_KEY` – your OpenAI API key.

Optional (for Pushover push notifications):
- `PUSHOVER_TOKEN`
- `PUSHOVER_USER`

### 4) Run the app
```bash
python app.py
```
Gradio will print a local URL in the terminal. Open it in your browser to start chatting.

## How it works (high level)

- `app.py` loads environment variables with `python-dotenv`.
- It initializes `OpenAI()` and sends/receives chat messages.
- When the model returns **tool calls**, the app routes them to built-in tools:
  - **Read PDF** – loads a local PDF with `pypdf.PdfReader`.
  - **Push notification** – sends a message to the Pushover API via `requests`.
- The Gradio `ChatInterface` provides a minimal UI.

## Notebooks

The `4_lab4.ipynb` notebook contains iterative development / experiments. It's not required to run the app, but is kept for reference.

## Configuration tips

- If you run in a cloud/remote environment, set `GRADIO_SERVER_NAME=0.0.0.0` and optionally `GRADIO_SERVER_PORT=7860` in your environment before launching.
- For production, consider setting `share=False` and using a reverse proxy.

## Testing

You can quickly sanity-check imports with:
```bash
python - <<'PY'
import gradio, openai, pypdf, dotenv, requests
print("All good!")
PY
```

## Troubleshooting

- **401 Unauthorized**: Ensure `OPENAI_API_KEY` is set in `.env` or the environment.
- **Pushover errors**: Set `PUSHOVER_TOKEN` and `PUSHOVER_USER`, or disable the notification tool.
- **PDF reading issues**: Verify file path and permissions; ensure `.pdf` files are not corrupted.

## License

MIT — see `LICENSE` (feel free to change to your preferred license).
