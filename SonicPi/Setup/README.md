# Local playback listener

Load [recording.rb](recording.rb) into Sonic Pi on the same computer as Python.
Enable incoming OSC in the IDE and configure `SONIC_PI_PORT` to match its port.
Reload this file when upgrading: requests now carry `[code, request_id, reply_port]`;
replies carry `[request_id, "OK: …" or "ERROR: …"]` on `/feedback`.

Review generated Ruby before sending it. This listener evaluates code and is
**not a sandbox**. OSC is unauthenticated; use only on a trusted local machine
with public-network access blocked. The acknowledgment confirms submission,
not the successful completion of asynchronous `live_loop` threads.

To test the protocol without executing code, run `python offline_demo.py` from
the repository root. See the root README for the isolated dependency set.
