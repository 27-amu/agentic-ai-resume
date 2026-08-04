import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app


def make_tool_call(name: str, arguments: str, call_id: str = "call-1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class NotificationTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_push_is_optional(self):
        self.assertEqual(
            app.push("hello"),
            {"sent": False, "reason": "Pushover is not configured"},
        )

    @patch("app.requests.post")
    @patch.dict(
        os.environ,
        {"PUSHOVER_TOKEN": "token", "PUSHOVER_USER": "user"},
        clear=True,
    )
    def test_push_uses_timeout(self, post):
        post.return_value.raise_for_status.return_value = None

        result = app.push("hello")

        self.assertEqual(result, {"sent": True})
        self.assertEqual(post.call_args.kwargs["timeout"], 10)

    @patch("app.push")
    def test_invalid_email_is_not_sent(self, push):
        result = app.record_user_details("not-an-email")

        self.assertEqual(
            result,
            {"recorded": False, "error": "A valid email address is required"},
        )
        push.assert_not_called()


class ToolDispatchTests(unittest.TestCase):
    def setUp(self):
        self.me = app.Me.__new__(app.Me)

    def test_unknown_tool_is_rejected(self):
        result = self.me.handle_tool_calls([make_tool_call("dangerous", "{}")])
        content = json.loads(result[0]["content"])
        self.assertEqual(content, {"error": "Unknown tool: dangerous"})

    def test_malformed_arguments_are_reported(self):
        result = self.me.handle_tool_calls(
            [make_tool_call("record_unknown_question", "not-json")]
        )
        content = json.loads(result[0]["content"])
        self.assertIn("error", content)

    @patch("app.record_unknown_question", return_value={"recorded": True})
    def test_known_tool_is_called(self, handler):
        with patch.dict(app.TOOL_HANDLERS, {"record_unknown_question": handler}):
            result = self.me.handle_tool_calls(
                [
                    make_tool_call(
                        "record_unknown_question",
                        json.dumps({"question": "What is your notice period?"}),
                    )
                ]
            )

        handler.assert_called_once_with(question="What is your notice period?")
        self.assertEqual(json.loads(result[0]["content"]), {"recorded": True})


if __name__ == "__main__":
    unittest.main()
