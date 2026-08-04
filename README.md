# Agentic AI Resume Chatbot

A Gradio portfolio chatbot that answers questions from a LinkedIn PDF and written profile summary. It uses an OpenAI-compatible model endpoint, supports bounded tool calls, and can optionally send contact or unanswered-question notifications through Pushover.

## Features

- Local-first setup with Ollama and `llama3.2:1b`
- Compatible with OpenAI and other OpenAI-compatible endpoints
- Resume-grounded answers from `me/linkedin.pdf` and `me/summary.txt`
- Explicitly whitelisted tools for contact requests and unanswered questions
- Consent-aware contact collection
- Timeouts, graceful notification failures, and bounded agent execution
- Gradio chat UI with example questions

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the configuration template:

   ```bash
   cp .env.example .env
   ```

4. Ensure Ollama is running and download the default model:

   ```bash
   ollama pull llama3.2:1b
   ollama serve
   ```

5. Run the application:

   ```bash
   python app.py
   ```

Open `http://127.0.0.1:7860` in a browser.

## Using OpenAI

Update `.env`:

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your-key
```

Do not commit `.env`; it is ignored by Git.

## Optional notifications

Set `PUSHOVER_TOKEN` and `PUSHOVER_USER` in `.env`. When they are absent or Pushover is unavailable, the chat continues and reports the notification failure internally.

Visitors must explicitly consent before the chatbot sends their contact details. Update the disclosure and handling policy before deploying publicly if your privacy requirements differ.

## Testing

```bash
python -m unittest discover -s tests -v
```

## Project structure

```text
app.py             Application and agent loop
me/linkedin.pdf    Resume source
me/summary.txt     Profile summary
tests/             Automated tests
.env.example       Configuration template
```

## License

MIT — see `LICENSE`.
