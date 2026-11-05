import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.analyzers.base import JSON_ONLY_SYSTEM_PROMPT, BaseAnalyzer


class DummyAnalyzer(BaseAnalyzer):
    def analyze(self, data):
        return data


def completion(content):
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class CallAiTests(unittest.TestCase):
    def setUp(self):
        client_patcher = patch("src.analyzers.base.OpenAI")
        sleep_patcher = patch("src.analyzers.base.time.sleep")
        self.create = client_patcher.start().return_value.chat.completions.create
        self.sleep = sleep_patcher.start()
        self.addCleanup(client_patcher.stop)
        self.addCleanup(sleep_patcher.stop)
        self.analyzer = DummyAnalyzer(api_key="key", base_url="https://example.com", model="glm")
        self.user_messages = [{"role": "user", "content": "요약"}]

    def test_inserts_json_system_prompt_when_missing(self):
        self.create.return_value = completion('{"ok": true}')

        self.analyzer._call_ai(self.user_messages)

        sent = self.create.call_args.kwargs["messages"]
        self.assertEqual(sent[0], {"role": "system", "content": JSON_ONLY_SYSTEM_PROMPT})
        self.assertEqual(sent[1:], self.user_messages)
        self.assertEqual(len(self.user_messages), 1)

    def test_keeps_existing_system_prompt(self):
        self.create.return_value = completion('{"ok": true}')
        messages = [{"role": "system", "content": "기존"}, *self.user_messages]

        self.analyzer._call_ai(messages)

        self.assertEqual(self.create.call_args.kwargs["messages"], messages)

    def test_requests_json_object_response_format(self):
        self.create.return_value = completion('{"ok": true}')

        self.analyzer._call_ai(self.user_messages)

        self.assertEqual(
            self.create.call_args.kwargs["response_format"], {"type": "json_object"}
        )

    def test_retries_without_response_format_in_same_attempt(self):
        self.create.side_effect = [
            Exception("Unsupported parameter: response_format"),
            completion('{"ok": true}'),
        ]

        self.assertEqual(self.analyzer._call_ai(self.user_messages), {"ok": True})

        self.assertEqual(self.create.call_count, 2)
        self.assertIn("response_format", self.create.call_args_list[0].kwargs)
        self.assertNotIn("response_format", self.create.call_args_list[1].kwargs)
        self.sleep.assert_not_called()

    def test_other_errors_use_existing_retry_without_dropping_response_format(self):
        self.create.side_effect = Exception("rate limited")

        with self.assertRaises(Exception):
            self.analyzer._call_ai(self.user_messages)

        self.assertEqual(self.create.call_count, 3)
        for call in self.create.call_args_list:
            self.assertIn("response_format", call.kwargs)

    def test_parses_code_fenced_json(self):
        self.create.return_value = completion('\n```json\n{"ok": true}\n```\n')

        self.assertEqual(self.analyzer._call_ai(self.user_messages), {"ok": True})

    def test_extracts_first_balanced_object_from_surrounding_text(self):
        self.create.return_value = completion(
            '결과입니다: {"a": {"b": "}{"}, "c": "\\"}"} 끝 {"other": 1}'
        )

        self.assertEqual(
            self.analyzer._call_ai(self.user_messages),
            {"a": {"b": "}{"}, "c": '"}'},
        )

    def test_unparseable_content_fails_after_three_attempts(self):
        self.create.return_value = completion("JSON이 아닌 응답 {미완성")

        with self.assertRaises(ValueError):
            self.analyzer._call_ai(self.user_messages)

        self.assertEqual(self.create.call_count, 3)

    def test_empty_content_fails_after_three_attempts(self):
        self.create.return_value = completion(None)

        with self.assertRaises(ValueError):
            self.analyzer._call_ai(self.user_messages)

        self.assertEqual(self.create.call_count, 3)

    def test_non_dict_json_is_rejected(self):
        self.create.return_value = completion("[1, 2]")

        with self.assertRaises(ValueError):
            self.analyzer._call_ai(self.user_messages)
