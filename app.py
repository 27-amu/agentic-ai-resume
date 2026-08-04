import json
import os
import re
from pathlib import Path
from typing import Any

import gradio as gr
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader


load_dotenv()

APP_DIR = Path(__file__).resolve().parent
PROFILE_PDF = APP_DIR / "me" / "linkedin.pdf"
PROFILE_SUMMARY = APP_DIR / "me" / "summary.txt"
DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.2:1b"
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def positive_env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


MAX_TOOL_ROUNDS = positive_env_int("MAX_TOOL_ROUNDS", 5)
MODEL_TIMEOUT_SECONDS = positive_env_int("MODEL_TIMEOUT_SECONDS", 60)
PUSHOVER_TIMEOUT_SECONDS = positive_env_int("PUSHOVER_TIMEOUT_SECONDS", 10)
MAX_MESSAGE_LENGTH = positive_env_int("MAX_MESSAGE_LENGTH", 4_000)


def push(text: str) -> dict[str, Any]:
    """Send an optional Pushover notification without breaking the chat."""
    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")
    if not token or not user:
        return {"sent": False, "reason": "Pushover is not configured"}

    try:
        response = requests.post(
            PUSHOVER_URL,
            data={"token": token, "user": user, "message": text},
            timeout=PUSHOVER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return {"sent": False, "reason": f"Notification failed: {exc.__class__.__name__}"}

    return {"sent": True}


def record_user_details(
    email: str, name: str = "Name not provided", notes: str = "Not provided"
) -> dict[str, Any]:
    email = email.strip()
    if not EMAIL_PATTERN.fullmatch(email):
        return {"recorded": False, "error": "A valid email address is required"}
    notification = push(f"Contact request from {name}: {email}. Notes: {notes}")
    return {"recorded": notification["sent"], "notification": notification}


def record_unknown_question(question: str) -> dict[str, Any]:
    notification = push(f"Unanswered resume question: {question}")
    return {"recorded": notification["sent"], "notification": notification}


RECORD_USER_DETAILS_SCHEMA = {
    "name": "record_user_details",
    "description": (
        "Record contact details only after the user explicitly asks to connect, "
        "provides an email address, and consents to it being recorded."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "The user's email address"},
            "name": {"type": "string", "description": "The user's name, if provided"},
            "notes": {
                "type": "string",
                "description": "Non-sensitive context the user asked to share",
            },
        },
        "required": ["email"],
        "additionalProperties": False,
    },
}

RECORD_UNKNOWN_QUESTION_SCHEMA = {
    "name": "record_unknown_question",
    "description": "Record a relevant career question that the supplied profile cannot answer.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The unanswered question"}
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

TOOLS = [
    {"type": "function", "function": RECORD_USER_DETAILS_SCHEMA},
    {"type": "function", "function": RECORD_UNKNOWN_QUESTION_SCHEMA},
]

TOOL_HANDLERS = {
    "record_user_details": record_user_details,
    "record_unknown_question": record_unknown_question,
}


class Me:
    def __init__(self) -> None:
        self.name = os.getenv("PROFILE_NAME", "Amit Kumar")
        self.model = os.getenv("LLM_MODEL", DEFAULT_MODEL)
        base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).strip()
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "ollama"
        self.openai = OpenAI(base_url=base_url, api_key=api_key)
        self.linkedin = self._read_pdf(PROFILE_PDF)
        self.summary = self._read_text(PROFILE_SUMMARY)

    @staticmethod
    def _read_pdf(path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(f"Profile PDF not found: {path}")
        return "\n".join(
            text
            for page in PdfReader(path).pages
            if (text := page.extract_text())
        )

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(f"Profile summary not found: {path}")
        return path.read_text(encoding="utf-8")

    def handle_tool_calls(self, tool_calls: list[Any]) -> list[dict[str, str]]:
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            handler = TOOL_HANDLERS.get(tool_name)
            try:
                arguments = json.loads(tool_call.function.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("Tool arguments must be a JSON object")
                if handler is None:
                    raise ValueError(f"Unknown tool: {tool_name}")
                result = handler(**arguments)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                result = {"error": str(exc)}

            results.append(
                {
                    "role": "tool",
                    "content": json.dumps(result),
                    "tool_call_id": tool_call.id,
                }
            )
        return results

    def system_prompt(self) -> str:
        return f"""You are the AI representative for {self.name}'s portfolio website.
Answer questions about {self.name}'s career, background, skills, and experience using only the supplied profile. Be professional, warm, and concise. Clearly say when the profile does not contain an answer; never invent credentials or experience. For a relevant unanswered career question, use record_unknown_question.

If a user wants to connect, explain that their details will be sent privately to {self.name}. Use record_user_details only after the user explicitly consents and provides an email address. Do not pressure visitors to share personal information or put sensitive information in notes.

## Summary
{self.summary}

## LinkedIn profile
{self.linkedin}
"""

    def chat(self, message: str, history: list[dict[str, Any]]) -> str:
        if len(message) > MAX_MESSAGE_LENGTH:
            return (
                f"Please shorten your message to {MAX_MESSAGE_LENGTH:,} characters or fewer."
            )

        messages = [
            {"role": "system", "content": self.system_prompt()},
            *history,
            {"role": "user", "content": message},
        ]

        try:
            for _ in range(MAX_TOOL_ROUNDS + 1):
                response = self.openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    timeout=MODEL_TIMEOUT_SECONDS,
                )
                choice = response.choices[0]
                if choice.finish_reason != "tool_calls":
                    return choice.message.content or "I couldn't generate a response."

                assistant_message = choice.message
                messages.append(assistant_message)
                messages.extend(self.handle_tool_calls(assistant_message.tool_calls or []))
        except Exception as exc:
            print(f"Chat request failed: {exc}", flush=True)
            return "I’m temporarily unable to reach the language model. Please try again shortly."

        return "I stopped because the request required too many tool actions. Please try rephrasing it."


def create_interface() -> gr.ChatInterface:
    me = Me()
    return gr.ChatInterface(
        fn=me.chat,
        title=f"Chat with {me.name}'s AI representative",
        description=(
            "Ask about experience, projects, and skills. Contact details are shared only "
            "after you explicitly consent."
        ),
        examples=[
            "Tell me about your strongest project.",
            "What technologies have you worked with?",
            "Why should I hire you?",
        ],
    )


if __name__ == "__main__":
    create_interface().launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        share=False,
    )
