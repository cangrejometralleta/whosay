#!/usr/bin/env python3
"""
test_whonews — how whonews picks a backend, and what it says when none answers.

Covers the resolution order — which provider answers, with which credential,
against which url — and the fallback chain a silent model drops into. The
network is never touched; the provider calls are exercised with _post_json
swapped for a recorder.

    python3 -m unittest test_whonews -v
"""

import io
import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import whocast  # noqa: E402
import whonews  # noqa: E402


# The variables that steer a backend; every test starts with none of them.
BACKEND_ENV = ("WHONEWS_PROVIDER", "WHONEWS_MODEL", "ANTHROPIC_API_KEY",
               "ANTHROPIC_BASE_URL", "OPENAI_API_KEY", "OPENAI_BASE_URL",
               "LLAMA_HOST")


def clear_backend_env(**overrides):
    """ClearBackendEnv Returns a patcher that Drops every backend Variable,
       then Sets the given ones."""
    env = {k: v for k, v in os.environ.items() if k not in BACKEND_ENV}
    env.update(overrides)
    return mock.patch.dict(os.environ, env, clear=True)


def spoken(printed):
    """Spoken Returns what the bubble Says as one line, with its borders and Wrapping undone."""
    said, inside = [], False
    for line in printed.splitlines():
        text = line.strip()
        if not inside:
            inside = text.startswith("_")
            continue
        if text.startswith("-"):
            break
        said.append(text[1:-1].strip())
    return " ".join(said)


def parse_args(*argv):
    """ParseArgs Runs the whonews parser over argv, with the cache Off."""
    return whonews.parse_whonews_args(["--no-cache", *argv])


class ResolveDefaultProviderTest(unittest.TestCase):
    """ResolveDefaultProviderTest Pins which backend answers when nobody asked for one."""

    def test_the_local_server_is_the_default(self):
        with clear_backend_env():
            self.assertEqual(parse_args().provider, "ollama")

    def test_a_key_in_the_environment_does_not_pick_a_paid_provider(self):
        with clear_backend_env(ANTHROPIC_API_KEY="sk-ant-env", OPENAI_API_KEY="sk-oai-env"):
            self.assertEqual(parse_args().provider, "ollama")

    def test_a_key_on_the_command_line_does_not_pick_one_either(self):
        with clear_backend_env():
            args = parse_args("--anthropic-key", "sk-ant-flag", "--openai-key", "sk-oai-flag")
            self.assertEqual(args.provider, "ollama")

    def test_whonews_provider_moves_off_the_local_server(self):
        with clear_backend_env(WHONEWS_PROVIDER="anthropic"):
            self.assertEqual(parse_args().provider, "anthropic")

    def test_the_flag_outranks_everything(self):
        with clear_backend_env(WHONEWS_PROVIDER="anthropic", ANTHROPIC_API_KEY="sk-ant"):
            self.assertEqual(parse_args("--provider", "ollama").provider, "ollama")


class ResolveApiKeyTest(unittest.TestCase):
    """ResolveApiKeyTest Pins where each backend's Credential comes from."""

    def test_flag_beats_environment(self):
        with clear_backend_env(ANTHROPIC_API_KEY="sk-ant-env", OPENAI_API_KEY="sk-oai-env"):
            args = parse_args("--anthropic-key", "sk-ant-flag", "--openai-key", "sk-oai-flag")
            self.assertEqual(whonews.resolve_api_key("anthropic", args), "sk-ant-flag")
            self.assertEqual(whonews.resolve_api_key("openai", args), "sk-oai-flag")

    def test_environment_fills_in(self):
        with clear_backend_env(ANTHROPIC_API_KEY="sk-ant-env", OPENAI_API_KEY="sk-oai-env"):
            args = parse_args()
            self.assertEqual(whonews.resolve_api_key("anthropic", args), "sk-ant-env")
            self.assertEqual(whonews.resolve_api_key("openai", args), "sk-oai-env")

    def test_missing_key_is_none(self):
        with clear_backend_env():
            self.assertIsNone(whonews.resolve_api_key("anthropic", parse_args()))

    def test_the_local_server_needs_none(self):
        with clear_backend_env():
            self.assertIsNone(whonews.resolve_api_key("ollama", parse_args()))


class ResolveBaseUrlTest(unittest.TestCase):
    """ResolveBaseUrlTest Pins which Endpoint each backend talks to."""

    def test_defaults(self):
        with clear_backend_env():
            args = parse_args()
            self.assertEqual(whonews.resolve_base_url("anthropic", args), "https://api.anthropic.com")
            self.assertEqual(whonews.resolve_base_url("openai", args), "https://api.openai.com")
            self.assertEqual(whonews.resolve_base_url("ollama", args), "http://127.0.0.1:8080")

    def test_environment_overrides_the_default(self):
        with clear_backend_env(ANTHROPIC_BASE_URL="https://gateway.example/anthropic",
                               OPENAI_BASE_URL="https://gateway.example/openai",
                               LLAMA_HOST="10.0.0.9:9000"):
            args = parse_args()
            self.assertEqual(whonews.resolve_base_url("anthropic", args),
                             "https://gateway.example/anthropic")
            self.assertEqual(whonews.resolve_base_url("openai", args),
                             "https://gateway.example/openai")
            self.assertEqual(whonews.resolve_base_url("ollama", args), "http://10.0.0.9:9000")

    def test_flag_beats_environment(self):
        with clear_backend_env(ANTHROPIC_BASE_URL="https://env.example",
                               OPENAI_BASE_URL="https://env.example"):
            args = parse_args("--anthropic-url", "https://flag.example",
                              "--openai-url", "https://flag.example/v")
            self.assertEqual(whonews.resolve_base_url("anthropic", args), "https://flag.example")
            self.assertEqual(whonews.resolve_base_url("openai", args), "https://flag.example/v")

    def test_an_empty_flag_falls_back_to_the_default(self):
        with clear_backend_env():
            args = parse_args("--anthropic-url", "", "--openai-url", "", "--ollama-url", "")
            self.assertEqual(whonews.resolve_base_url("anthropic", args), "https://api.anthropic.com")
            self.assertEqual(whonews.resolve_base_url("openai", args), "https://api.openai.com")
            self.assertEqual(whonews.resolve_base_url("ollama", args), "http://127.0.0.1:8080")

    def test_scheme_is_filled_in_and_the_trailing_slash_dropped(self):
        with clear_backend_env():
            args = parse_args("--anthropic-url", "proxy.example:8443/")
            self.assertEqual(whonews.resolve_base_url("anthropic", args),
                             "http://proxy.example:8443")


class BuildModelBackendTest(unittest.TestCase):
    """BuildModelBackendTest Pins the Backend the Session carries."""

    def test_key_and_url_reach_the_backend(self):
        with clear_backend_env():
            backend = whonews.build_model_backend(
                parse_args("--provider", "anthropic",
                           "--anthropic-key", "sk-ant", "--anthropic-url", "https://proxy.example"))
            self.assertEqual(backend.provider, "anthropic")
            self.assertEqual(backend.api_key, "sk-ant")
            self.assertEqual(backend.base_url, "https://proxy.example")
            self.assertEqual(backend.model, whonews.DEFAULT_MODELS["anthropic"])

    def test_each_provider_falls_back_to_its_own_url(self):
        for provider, url in (("ollama", "http://127.0.0.1:8080"),
                              ("anthropic", "https://api.anthropic.com"),
                              ("openai", "https://api.openai.com")):
            with self.subTest(provider=provider), clear_backend_env():
                backend = whonews.build_model_backend(parse_args("--provider", provider))
                self.assertEqual(backend.base_url, url)
                self.assertEqual(backend.base_url, whonews.PROVIDER_PORTS[provider].default_url)

    def test_model_flag_beats_the_provider_default(self):
        with clear_backend_env(WHONEWS_MODEL="from-the-env"):
            self.assertEqual(whonews.build_model_backend(parse_args()).model, "from-the-env")
            self.assertEqual(
                whonews.build_model_backend(parse_args("--model", "from-the-flag")).model,
                "from-the-flag")

    def test_only_the_chosen_provider_is_resolved(self):
        with clear_backend_env(OPENAI_API_KEY="sk-oai"):
            backend = whonews.build_model_backend(parse_args("--provider", "ollama"))
            self.assertEqual(backend.provider, "ollama")
            self.assertIsNone(backend.api_key)


class ProviderCallTest(unittest.TestCase):
    """ProviderCallTest Pins the Url and Headers each backend Posts with."""

    def setUp(self):
        self.sent = []

    def record(self, reply):
        """Record Returns a _post_json stand-in that Remembers the call, then Answers reply."""
        def _post_json(url, body, timeout, headers=None):
            self.sent.append({"url": url, "body": body, "timeout": timeout,
                              "headers": headers or {}})
            return reply
        return _post_json

    def backend(self, *argv, **env):
        """Backend Returns the Backend argv and env Resolve to."""
        with clear_backend_env(**env):
            return whonews.build_model_backend(parse_args(*argv))

    def test_anthropic_posts_to_the_given_url_with_the_given_key(self):
        backend = self.backend("--provider", "anthropic",
                               "--anthropic-key", "sk-ant", "--anthropic-url", "https://proxy.example")
        reply = {"content": [{"type": "text", "text": "una toma"}]}
        with mock.patch.object(whonews, "_post_json", self.record(reply)):
            answer = whonews._call_anthropic("persona", "prompt", backend)
        self.assertEqual(answer, "una toma")
        call = self.sent[0]
        self.assertEqual(call["url"], "https://proxy.example/v1/messages")
        self.assertEqual(call["headers"]["x-api-key"], "sk-ant")
        self.assertEqual(call["body"]["model"], whonews.DEFAULT_MODELS["anthropic"])

    def test_openai_posts_to_the_given_url_with_the_given_key(self):
        backend = self.backend("--provider", "openai",
                               "--openai-key", "sk-oai", "--openai-url", "https://proxy.example")
        reply = {"choices": [{"message": {"content": "a take"}}]}
        with mock.patch.object(whonews, "_post_json", self.record(reply)):
            answer = whonews._call_openai("persona", "prompt", backend)
        self.assertEqual(answer, "a take")
        call = self.sent[0]
        self.assertEqual(call["url"], "https://proxy.example/v1/chat/completions")
        self.assertEqual(call["headers"]["Authorization"], "Bearer sk-oai")

    def test_the_local_server_posts_to_its_host(self):
        backend = self.backend("--provider", "ollama", LLAMA_HOST="127.0.0.1:9999")
        reply = {"choices": [{"message": {"content": "local take"}}]}
        with mock.patch.object(whonews, "_post_json", self.record(reply)):
            answer = whonews._call_ollama("persona", "prompt", backend)
        self.assertEqual(answer, "local take")
        self.assertEqual(self.sent[0]["url"], "http://127.0.0.1:9999/v1/chat/completions")

    def test_a_keyless_provider_says_which_key_is_missing(self):
        with self.assertRaisesRegex(RuntimeError, "--anthropic-key"):
            whonews._call_anthropic("persona", "prompt",
                                    self.backend("--provider", "anthropic"))
        with self.assertRaisesRegex(RuntimeError, "--openai-key"):
            whonews._call_openai("persona", "prompt", self.backend("--provider", "openai"))


class SessionBackendTest(unittest.TestCase):
    """SessionBackendTest Pins that the Session carries the Backend all the way to the Call."""

    def test_a_joke_reaches_the_configured_endpoint(self):
        with clear_backend_env():
            args = parse_args("--provider", "anthropic", "--anthropic-key", "sk-ant",
                              "--anthropic-url", "https://proxy.example", "--no-color")
            character, char = whonews.resolve_requested_character(args)
            session = whonews.build_news_session(character, char, args)

        self.assertEqual(session.backend.provider, "anthropic")

        sent = {}

        def _post_json(url, body, timeout, headers=None):
            sent.update(url=url, headers=headers or {}, timeout=timeout)
            return {"content": [{"type": "text", "text": "Ay, no puede ser."}]}

        with mock.patch.object(whonews, "_post_json", _post_json), \
                mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(whonews.run_joke_command(session), 0)

        self.assertEqual(sent["url"], "https://proxy.example/v1/messages")
        self.assertEqual(sent["headers"]["x-api-key"], "sk-ant")
        self.assertEqual(sent["timeout"], args.timeout)


class SilentModelTest(unittest.TestCase):
    """SilentModelTest Pins what a run prints when the model never answers."""

    CHARACTER = "carmen_gloria"

    def setUp(self):
        with clear_backend_env():
            self.args = whonews.parse_whonews_args(
                ["-C", self.CHARACTER, "--db", ":memory:", "--no-color"])
        self.char = whocast.load_character(self.CHARACTER)
        self.session = whonews.build_news_session(self.CHARACTER, self.char, self.args)

    def opine(self, stories):
        """Opine Runs one opine Command against a Provider that refuses to answer,
           then Returns its exit Code and what it printed."""
        def refuse(persona, prompt, backend):
            raise urllib.error.URLError("connection refused")

        out = io.StringIO()
        with mock.patch.dict(whonews.PROVIDERS, {"ollama": refuse}), \
                mock.patch("sys.stdout", out), mock.patch("sys.stderr", io.StringIO()):
            code = whonews.run_opine_command(self.session, self.args, stories)
        return code, out.getvalue()

    def test_an_empty_archive_falls_back_to_the_canned_line(self):
        code, printed = self.opine([("Hoy pasó algo", "Diario")])
        self.assertEqual(code, 0)
        self.assertEqual(spoken(printed), self.char["fallback"])
        self.assertNotIn("Hoy pasó algo", printed)

    def test_the_archive_answers_instead(self):
        whonews.store_take(self.session.db, "Titular de ayer", self.session.backend.model,
                           self.CHARACTER, "Diario", "Lo dije ayer y lo sostengo.")
        code, printed = self.opine([("Hoy pasó algo", "Diario")])
        self.assertEqual(code, 0)
        self.assertEqual(spoken(printed), "Lo dije ayer y lo sostengo.")
        self.assertIn("Titular de ayer", printed)
        self.assertNotIn("Hoy pasó algo", printed)

    def test_a_character_without_a_fallback_says_its_signature(self):
        char = dict(self.char)
        char.pop("fallback")
        session = whonews.build_news_session(self.CHARACTER, char, self.args)
        self.assertEqual(session.fallback, char["signature"])

    def test_a_silent_joke_still_prints_a_panel(self):
        def refuse(persona, prompt, backend):
            raise urllib.error.URLError("connection refused")

        out = io.StringIO()
        with mock.patch.dict(whonews.PROVIDERS, {"ollama": refuse}), \
                mock.patch("sys.stdout", out), mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(whonews.run_joke_command(self.session), 0)
        self.assertEqual(spoken(out.getvalue()), self.char["fallback"])


if __name__ == "__main__":
    unittest.main()
