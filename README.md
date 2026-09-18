# Sonic Pi Composer Agents

## Reproduce the review loop without API keys

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-offline.txt
python -m pytest App/tests -q
python offline_demo.py
```

Read the [complete review trace](results/offline/review-trace.json) and
[resulting arpeggio fixture](results/offline/arpeggio.rb). For each of the OpenAI,
Azure, and Anthropic adapters, a scripted draft receives an error; the next
request includes that error and supplies a corrected draft. Real loopback UDP
messages exercise the transport. A separate lost-reply case times out rather
than hanging, and stale success replies are ignored.

**What this proves:** bounded request/reply handling, cleanup, and feedback
propagation through the actual review loop. **What it does not prove:** these
are deliberately scripted model replies and runtime acknowledgments, not model
quality, Ruby execution, audio rendering, or mastering. No provider calls,
microphone access, Sonic Pi installation or API keys are needed. Eight offline
tests pass; the real Sonic Pi integration test is opt-in.

The transport now returns feedback (previously it returned `None`), resets
request state, correlates replies by ID, and uses a bounded timeout. Review
errors are passed into the next provider request instead of being discarded or
appended to a nonexistent message list. Azure receives its deployment name in
the model field; Anthropic receives a message list rather than a string.

**Upgrade note:** reload [recording.rb](SonicPi/Setup/recording.rb) in Sonic Pi.
The old uncorrelated listener is incompatible and will now time out. This
listener is for Sonic Pi and Python running on the **same computer**. Review all
generated Ruby before playback: `eval` is not a sandbox, and OSC has no
authentication. Keep it on a trusted local machine, never expose it publicly.
An `OK` acknowledges submission, not completion of every asynchronous loop.

## Table of Contents
1. [Introduction](#introduction)
2. [How It Works](#how-it-works)
3. [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [API Setup](#api-setup)
    - [Installation](#installation)
    - [Working with Samples](#working-with-samples)
4. [Configuration](#configuration)
5. [Running the System](#running-the-system)
   - [Web Application](#web-application)
   - [Command Line Interface](#command-line-interface)
6. [Output Files](#output-files)
7. [Verification](#verification)

---

## Introduction

This system coordinates role-specific model prompts to design a song, generate
Sonic Pi code, review revisions, and package the resulting artifacts. A web
interface exposes the agent trace and code history; an OSC integration sends
approved code to a running Sonic Pi instance.

> **Status:** working research prototype. Core composition and web workflows
> are implemented; automated recording is currently Windows-specific and output
> quality depends on the selected model provider and configuration.

## How It Works

[Watch Music Agent in action](https://www.youtube.com/watch?v=rcfCjKbLkK0)

The system uses specialized AI assistants, each handling different aspects of music creation. These agents work together through multiple phases, starting from your initial input and preferences.

The system includes the following specialized roles (configured in `ArtistConfig.json`):
- **Artist** - Overall creative direction
- **Composer** - Musical composition
- **Songwriter** - Lyrics and songwriting
- **Arranger** - Musical arrangement
- **Sonic PI Coder** - Code generation for Sonic Pi
- **Sonic PI Reviewer** - Code review and quality assurance
- **Sonic PI Mix Engineer** - Audio mixing
- **Master Engineer** - Final mastering
- **Music Publisher** - Final output generation

The workflow consists of four main phases:

### 1. Design Phase
Initial planning and conceptualization of the song.

### 2. Creation Phase
Generation of the Sonic Pi script, initial playback testing, iterative review (by agents or humans), and code refinement.

### 3. Mastering Phase
Audio mixing and mastering to polish the final track.

### 4. Publishing Phase
Final output generation including the Sonic Pi script file, album cover artwork, booklet, and optional audio recording.

The final output includes a booklet with album cover art, lyrics, technical information, and the complete Sonic Pi code file (`.rb` format).

## Getting Started

### Prerequisites

- **Sonic Pi**: Required to run the generated `.rb` files. Download from: https://sonic-pi.net/
- **Python**: Version 3.12

### API Setup

The system supports multiple AI providers. You can use OpenAI, Anthropic, or Azure OpenAI APIs. Note that Anthropic doesn't support image generation, so album covers won't be created when using that provider.

Set API keys as environment variables. Never commit credentials to a settings
or configuration file:

**OPENAI_API_KEY:**
- On macOS/Linux:
  ```bash
  export OPENAI_API_KEY='<your_api_key>'
  ```
- On Windows (PowerShell):
  ```bash
  $env:OPENAI_API_KEY='<your_api_key>'
  ```

**ANTHROPIC_API_KEY:**
- On macOS/Linux:
  ```bash
  export ANTHROPIC_API_KEY='<your_api_key>'
  ```
- On Windows (PowerShell):
  ```bash
  $env:ANTHROPIC_API_KEY='<your_api_key>'
  ```

**AZURE_OPENAI_API_KEY:**
- On macOS/Linux:
  ```bash
  export AZURE_OPENAI_API_KEY='<your_api_key>'
  ```
- On Windows (PowerShell):
  ```bash
  $env:AZURE_OPENAI_API_KEY='<your_api_key>'
  ```

Keep secrets out of the tracked settings file; use environment variables.

### Installation

```bash
# Clone the repository
git clone https://github.com/takakhoo/sonic-pi-composer-agents.git

# Navigate to the project directory
cd sonic-pi-composer-agents

# Install Python dependencies
pip install -r requirements.txt
```

**Note:** If you plan to use Anthropic's API, you'll also need to install Rust: https://www.rust-lang.org/tools/install

### Working with Samples

You can add your own audio samples to the `Samples` folder. The folder comes with a base set of samples, but you can easily extend it by adding new sample files.

To use samples in your compositions, the system needs metadata describing each sample. This information helps the AI agents make better musical decisions.

When you add new sample packs, regenerate the metadata by running:

```bash
python SampleMedataListing.py
```

This generates a JSON file with sample metadata in the following format:

```json
{
    "Filename": "Synth/Prophet REV2 KEYS Echo Low - C.wav",
    "Duration": 3.2,
    "BPM": 161.5,
    "Key": "A minor",
    "Vibe": "The track has a Energetic tempo at 161 BPM, featuring a warm and high energy sound. It feels soft and smooth with a A minor tonality.",
    "Tags": [
        "Energetic",
        "warm",
        "high energy",
        "soft and smooth",
        "A minor",
        "Whale vocalization",
        "Keyboard (musical)",
        "Piano",
        "Ukulele",
        "Music"
    ],
    "Description": "A warm, high energy track with a Energetic tempo and a A minor tonality.",
    "Track Type": "Instrumentals Only"
}
```

The system uses Yamnet for sample classification. More details can be found in the [Yamnet README](App/inc/yamnet-tensorflow2-yamnet-v1/README.md).

## Configuration

Keep API keys in environment variables. Do not write credentials into tracked
files under `AgentConfig/`. You can adjust non-secret provider and workflow
settings in those files as needed.

The system comes with several artist configurations:

- **Basic**: Standard music creation workflow
- **Eval**: Includes Sonic Pi code evaluation via a running Sonic Pi instance
- **Full**: Includes code evaluation and automatic recording (Windows only currently)
- **Art**: Only generates album cover artwork (no song generation)

For the Eval and Full configurations, you'll need additional setup:

1. **Launch Sonic Pi** on your machine
2. **Configure connection**: Update `ArtistConfig.json` with the correct `sonic_pi_IP` and `sonic_pi_port` (found in Sonic Pi IDE via menu > IO). Make sure incoming OSC messages are allowed.
3. **Set up the listener**: Load the current `SonicPi/Setup/recording.rb` in
Sonic Pi on the same computer. It echoes each request ID and replies to the
temporary loopback port included by the client. Do not use an older copy.

4. Once running, you'll see the listener active in your Cues panel, enabling Sonic Pi to execute your generated code and send feedback back to the system.

## Running the System

You can run the system in two ways: through a web application or via the command line.

### Web Application

The easiest way to get started is using the `start_musicagent.bat` script in the main folder, which launches both the backend and frontend.

You can also run them separately:

**Backend:**
```bash
cd App && python app.py
```

**Frontend:**
```bash
cd Frontend && npm run serve
```

The web interface visualizes the music creation process and lets you interact with the AI agents. You can view the conversation history with different agents, check generated Sonic Pi code versions, and even send code directly to the Sonic Pi IDE.

For more details on using the web application, see the [Music Agent App README](App/README.md).

### Command Line Interface

For command-line usage, run:

```bash
python run.py
```

You'll be prompted to:
- Choose a configured model provider and model
- Provide song details: name, duration, style
- Optionally specify additional requests like chord progressions or musical influences

Example Sonic Pi code can be found in the `SonicPi/Examples` folder.

## Output Files

The system generates the following files in the `Songs` folder, organized in subdirectories named after each track:

- **Track File (`.rb`)**: The Sonic Pi code file. Load this in Sonic Pi to play your track.
  - When using the "Full" configuration, a WAV recording file is also created automatically.
- **Booklet**: Contains the album cover image, lyrics, and technical information about the track setup.
- **Log File**: Complete logging of the generation process. Useful for debugging if code is lost or incomplete.

If you're using the Full configuration and have your recording device properly configured (Windows only currently), recordings are made automatically.

## Verification

CI installs the small pinned offline requirements, runs eight regression tests,
replays all three provider adapters, and uploads the trace. It also compiles the
Python sources. The live integration test skips unless explicitly enabled.

Model-provider calls, live OSC execution, and Windows audio capture are
integration tests and require the credentials or applications described above.
