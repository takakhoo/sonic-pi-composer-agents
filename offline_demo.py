"""Exercise real UDP transport + agent review with scripted peers, never Ruby eval."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import argparse
import json
import logging
import threading

from pythonosc import dispatcher, osc_server, udp_client
from App.services.agent import GPTAgent
from App.services.sonicPi import SonicPi

LOGGER = logging.getLogger("offline-demo")


@contextmanager
def scripted_peer(replies, *, send_stale=False):
    """Local test peer: acknowledges text, DOES NOT execute or validate Ruby."""
    captured = []
    answers = iter(replies)
    disp = dispatcher.Dispatcher()

    def receive(address, script, request_id, reply_port):
        captured.append(script)
        reply = next(answers, None)
        client = udp_client.SimpleUDPClient("127.0.0.1", reply_port)
        try:
            if send_stale:
                client.send_message("/feedback", ["old-request", "OK: stale feedback"])
            if reply is not None:
                client.send_message("/feedback", [request_id, reply])
        finally:
            client.close()

    disp.map("/run-code", receive)
    server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 0), disp)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], captured
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def replay(provider="openai"):
    song = Mock(name="fixture-song")
    song.song_dir = "offline-fixture-not-written"
    agent = GPTAgent("fixture-model", LOGGER, song, "Basic", provider)
    agent.check_token_limit = Mock(return_value=True)
    transport = SonicPi(LOGGER)
    scripts = ["use_synth :nonexistent\nplay 60", "use_bpm 96\nuse_synth :piano\n"
               "2.times do\n  [60, 64, 67, 71, 69, 67, 64, 62].each do |n|\n"
               "    play n, release: 0.6, amp: 0.4\n    sleep 0.5\n  end\nend\n"]
    prompts = []

    def response(*args):
        prompts.append(deepcopy(args[-1]))
        return json.dumps({"sonicpi_code": scripts[min(len(prompts)-1, 1)]})

    setattr(agent, f"handle_{'azure_openai' if provider == 'azure' else provider}_request", response)
    with scripted_peer(["ERROR: unknown synth", "OK: corrected fixture accepted"], send_stale=True) as (port, captured):
        agent.run_sonic_pi_script = lambda *args: transport.call_sonicpi(
            song, "127.0.0.1", port, agent.song_creation_data.sonicpi_code, timeout=2)
        agent.discussion(None, "compose", agent.song_creation_data,
                         {"assistants": [{"name": "Composer", "system_instruction": ["Compose a short arpeggio."]}]},
                         {"compose": {"assistant_role_name": "Composer", "user_role_name": "Artist",
                                      "phase_prompt": ["Write eight beats in C major at 96 BPM."],
                                      "input": {}, "codeValidation": True}})
    return {"provider_adapter": provider, "mode": "scripted fixtures, no model calls or Ruby execution",
            "attempts": len(prompts), "scripts_sent": captured,
            "retry_receives_error": any("unknown synth" in m["content"] for m in prompts[-1]),
            "feedback": transport.feedback_message, "transport_cleaned_up": transport.server is None,
            "review_messages": agent.conversation_history}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results/offline"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = [replay(p) for p in ("openai", "azure", "anthropic")]
    timeout_transport = SonicPi(LOGGER)
    with scripted_peer([None], send_stale=True) as (port, _):
        try:
            timeout_transport.call_sonicpi(None, "127.0.0.1", port, "play 60", timeout=.1)
        except TimeoutError:
            timeout_result = "timed out; stale success ignored; server closed"
        else:
            raise AssertionError("stale reply incorrectly accepted")
    assert all(r["attempts"] == 2 and r["retry_receives_error"] and r["transport_cleaned_up"] for r in records)
    (args.output / "review-trace.json").write_text(json.dumps({"runs": records, "timeout_case": timeout_result}, indent=2) + "\n")
    (args.output / "arpeggio.rb").write_text(records[0]["scripts_sent"][-1])
    print(f"3 provider adapters: failed fixture → corrected fixture; timeout bounded. Results: {args.output}")


if __name__ == "__main__":
    main()
