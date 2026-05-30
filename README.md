# Remote Ollama Tunnel Chat

Tiny Python-first template for chatting with Ollama running on:

- this computer
- a LAN/home server
- any SSH-reachable Linux server
- an AWS/Azure/Linode/DigitalOcean/etc. VM
- a Google Compute Engine VM through `gcloud`

The niche: keep Ollama private on the server and reach it through a local SSH tunnel, with a tiny browser chat UI and no heavy web stack.

```text
Browser chat UI
  -> localhost:11435
  -> SSH tunnel, when needed
  -> server 127.0.0.1:11434
  -> Ollama
```

## What It Is Not

- Not Open WebUI
- Not Docker-based
- Not cloud-provider-specific
- Not a public Ollama gateway
- Not a VM lifecycle manager

The stop command never shuts down, reboots, deletes, or resizes a server or VM. It only stops local helper processes that this project started.

## Requirements

On your computer:

- Python 3.11 or newer
- `ssh` for generic remote servers
- optional: `gcloud` for Google Compute Engine mode

On a remote install target:

- Linux with systemd
- `sudo`
- internet access to download Ollama and models

## Quick Start

Copy the example config:

```bash
cp config/config.example.toml config/config.toml
```

On Windows PowerShell:

```powershell
Copy-Item .\config\config.example.toml .\config\config.toml
notepad .\config\config.toml
```

Choose one mode in `config/config.toml`.

### Local Ollama

Use this when Ollama already runs on your PC or a reachable LAN server.

```toml
[server]
mode = "local"
local_ollama_url = "http://localhost:11434"
local_ui_port = 8787
```

Start:

```bash
python scripts/remote_ollama_chat.py start
```

### Any SSH Server

Use this for a home server, AWS EC2, Azure VM, plain Linux VPS, etc.

```toml
[server]
mode = "ssh"
remote_ollama_host = "127.0.0.1"
remote_ollama_port = 11434
local_ollama_port = 11435
local_ui_port = 8787

[ssh]
host = "ubuntu@YOUR_SERVER"
port = 22
identity_file = ""
extra_args = []
```

Install Ollama on the server:

```bash
python scripts/remote_ollama_chat.py install
```

Start the tunnel and chat UI:

```bash
python scripts/remote_ollama_chat.py start
```

### Google Compute Engine

GCE is just an optional mode, not the core project.

```toml
[server]
mode = "gcloud"
remote_ollama_host = "127.0.0.1"
remote_ollama_port = 11434
local_ollama_port = 11435

[gcloud]
project = "YOUR_GCP_PROJECT_ID"
zone = "YOUR_GCP_ZONE"
instance = "YOUR_GCE_INSTANCE_NAME"
user = ""
tunnel_through_iap = false
```

Then:

```bash
python scripts/remote_ollama_chat.py install
python scripts/remote_ollama_chat.py start
```

## Windows Double-Click Files

For Windows users, these wrappers call the Python CLI:

```text
launchers/windows/Install Remote Ollama.bat
launchers/windows/Start Remote Ollama Chat.bat
launchers/windows/Stop Remote Ollama Chat.bat
```

They are optional. The real logic is in:

```text
scripts/remote_ollama_chat.py
```

## Commands

```bash
python scripts/remote_ollama_chat.py install
python scripts/remote_ollama_chat.py start
python scripts/remote_ollama_chat.py status
python scripts/remote_ollama_chat.py stop
```

## Security Defaults

- `config/config.toml` is ignored by git.
- Ollama is configured to listen on `127.0.0.1:11434` on remote installs.
- The chat UI talks to the remote server through a local tunnel.
- No public firewall rule is needed for Ollama.
- No cloud shutdown commands are included.

## Model Defaults

The example config installs:

```toml
models = [
  "llama3.2",
  "qwen3:8b"
]
```

Use small models first on CPU-only servers. The UI lists whatever Ollama reports from `/api/tags`.

## References

- [Ollama](https://github.com/ollama/ollama)
- [Ollama API docs](https://docs.ollama.com/api)
- [OpenSSH port forwarding](https://man.openbsd.org/ssh)
- [Google Cloud gcloud compute ssh](https://docs.cloud.google.com/sdk/gcloud/reference/compute/ssh)
- [GitHub secret scanning](https://docs.github.com/en/code-security/secret-scanning/enabling-secret-scanning-features)

## License

MIT
