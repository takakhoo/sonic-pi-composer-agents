import unittest
import os
from unittest.mock import MagicMock, patch
from App.services.sonicPi import SonicPi
from App.services.song import Song
import logging
import time

@unittest.skipUnless(
    os.environ.get("SONIC_PI_INTEGRATION") == "1",
    "requires a live Sonic Pi instance; set SONIC_PI_INTEGRATION=1 to run",
)
class TestSonicPiIntegration(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("SonicPiTest")
        self.logger.setLevel(logging.INFO)
        self.sonic_pi = SonicPi(self.logger)
        self.song = Song(name="TestSong", logger=self.logger)
        self.song.song_dir = "test_dir"
        self.ip_address = "127.0.0.1"
        self.port = int(os.environ.get("SONIC_PI_PORT", "4560"))
        self.full_script = "play 60"

    def test_call_sonicpi_integration(self):
        self.sonic_pi.call_sonicpi(self.song, self.ip_address, self.port, self.full_script)
        time.sleep(5)  # Wait for the script to execute and feedback to be received
        self.assertTrue(self.sonic_pi.feedback_received)
        self.assertTrue(self.sonic_pi.feedback_message.startswith("OK:"))

if __name__ == '__main__':
    unittest.main()
