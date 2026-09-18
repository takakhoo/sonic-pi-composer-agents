"""Bounded, correlated OSC requests to the local Sonic Pi listener.

Reload SonicPi/Setup/recording.rb after updating: replies now echo a request ID.
This is transport, not a Ruby sandbox. Review code before sending it to Sonic Pi.
"""
from pathlib import Path
import math
import threading
import uuid

from pythonosc import udp_client, dispatcher, osc_server


def feedback_succeeded(message):
    return isinstance(message, str) and message.startswith("OK:")


class SonicPi:
    def __init__(self, logger):
        self.logger = logger
        self.feedback_received = False
        self.feedback_message = ""
        self.server = self.server_thread = None
        self._request_id = None
        self._feedback = threading.Event()
        self._call_lock = threading.Lock()

    def handle_message(self, address, *args):
        if len(args) != 2 or args[0] != self._request_id or self._feedback.is_set():
            return  # Ignore stale, uncorrelated and duplicate datagrams.
        self.feedback_message = str(args[1])
        self.feedback_received = True
        self._feedback.set()
        self.logger.info("Sonic Pi feedback: %s", self.feedback_message)

    def shutdown_server(self):
        server, thread = self.server, self.server_thread
        if server is not None:
            if thread is not None and thread.is_alive():
                server.shutdown()
                thread.join()
            server.server_close()
        self.server = self.server_thread = None

    def read_script_from_file(self, file_path):
        return Path(file_path).read_text(encoding="utf-8")

    def call_sonicpi(self, song, ip_address, port, full_script=None, *, timeout=120,
                     feedback_port=0):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if full_script is None:
            full_script = self.read_script_from_file(Path(song.song_dir) / f"{song.name}.rb")
        if not isinstance(full_script, str) or not full_script.strip():
            raise ValueError("script must be nonempty text")
        if len(full_script.encode("utf-8")) > 60000:
            raise ValueError("script exceeds the safe OSC UDP payload budget")
        if not self._call_lock.acquire(blocking=False):
            raise RuntimeError("a Sonic Pi request is already in progress")
        try:
            self.feedback_received = False
            self.feedback_message = ""
            self._feedback.clear()
            self._request_id = uuid.uuid4().hex
            disp = dispatcher.Dispatcher()
            disp.map("/feedback", self.handle_message)
            self.server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", feedback_port), disp)
            self.server.daemon_threads = True
            self.server_thread = threading.Thread(
                target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            self.server_thread.start()
            client = udp_client.SimpleUDPClient(ip_address, port)
            try:
                client.send_message("/run-code", [full_script, self._request_id,
                                                self.server.server_address[1]])
                if not self._feedback.wait(timeout):
                    raise TimeoutError(f"No correlated Sonic Pi feedback within {timeout:g} seconds")
                return self.feedback_message
            finally:
                client.close()
        finally:
            self._request_id = None
            self.shutdown_server()
            self._call_lock.release()
