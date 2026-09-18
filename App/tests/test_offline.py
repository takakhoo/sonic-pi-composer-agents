import logging
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from App.services.sonicPi import SonicPi, feedback_succeeded
from App.services.agent import GPTAgent
from offline_demo import replay, scripted_peer


@pytest.mark.parametrize("provider", ["openai", "azure", "anthropic"])
def test_review_retries_with_feedback(provider):
    result = replay(provider)
    assert result["attempts"] == 2
    assert result["retry_receives_error"]
    assert result["transport_cleaned_up"]
    assert result["feedback"].startswith("OK:")
    assert result["scripts_sent"][0] != result["scripts_sent"][1]


def test_repeated_requests_reset_state_and_timeout():
    transport = SonicPi(logging.getLogger("test"))
    with scripted_peer(["OK: first", None], send_stale=True) as (port, received):
        assert transport.call_sonicpi(None, "127.0.0.1", port, "play 60", timeout=1) == "OK: first"
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            transport.call_sonicpi(None, "127.0.0.1", port, "play 62", timeout=.1)
        assert time.monotonic() - start < 2
        assert not transport.feedback_received
        assert transport.server is None
        assert received == ["play 60", "play 62"]


def test_file_loading_and_port_released(tmp_path):
    (tmp_path / "song.rb").write_text("play 64", encoding="utf-8")
    transport = SonicPi(logging.getLogger("test"))
    song = SimpleNamespace(name="song", song_dir=tmp_path)
    with scripted_peer(["ERROR: unknown note"]) as (port, received):
        result = transport.call_sonicpi(song, "127.0.0.1", port, timeout=1)
    assert not feedback_succeeded(result)
    assert received == ["play 64"]
    assert transport.server is None and transport.server_thread is None
    with pytest.raises(FileNotFoundError):
        transport.read_script_from_file(tmp_path / "missing.rb")


def test_invalid_requests_and_explicit_success():
    transport = SonicPi(logging.getLogger("test"))
    for timeout in (0, -1, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            transport.call_sonicpi(None, "localhost", 4560, "play 60", timeout=timeout)
    for script in ("", " ", "a" * 60001):
        with pytest.raises(ValueError):
            transport.call_sonicpi(None, "localhost", 4560, script)
    assert all(not feedback_succeeded(s) for s in [None, "unknown synth", "", "ERROR: failed"])
    assert feedback_succeeded("OK: accepted")


def test_timeout_enters_review_instead_of_succeeding():
    agent = GPTAgent("fixture", Mock(), Mock(), "Basic", "openai")
    agent.run_sonic_pi_script = Mock(side_effect=TimeoutError("offline"))
    assert not agent.validate_and_execute_code(agent.song_creation_data, {}, "draft")
    assert "offline" in agent.conversation_history[-1]["content"]


def test_azure_uses_deployment_as_model(monkeypatch):
    from App.config import Config
    monkeypatch.setattr(Config, "MODEL_CONFIG", {"azure": {"fixture": {"deployment_name": "my-deployment"}}})
    agent = GPTAgent("fixture", Mock(), Mock(), "Basic", "azure")
    agent.count_tokens = Mock(return_value=1)
    agent.log_request_response = Mock()
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])
    messages = [{"role": "user", "content": "compose"}]
    assert agent.handle_azure_openai_request(client, "", "compose", messages) == "ok"
    client.chat.completions.create.assert_called_once_with(model="my-deployment", messages=messages)
