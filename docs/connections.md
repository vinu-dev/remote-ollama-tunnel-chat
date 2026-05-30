# Connection Modes

## Local

Use local mode when Ollama is already reachable from your browser machine:

```toml
[server]
mode = "local"
local_ollama_url = "http://localhost:11434"
```

This is useful for:

- your own PC
- a LAN server that already exposes Ollama privately
- a corporate VPN/private network endpoint

## SSH

Use SSH mode for any server you can SSH into:

```toml
[server]
mode = "ssh"
remote_ollama_host = "127.0.0.1"
remote_ollama_port = 11434
local_ollama_port = 11435

[ssh]
host = "ubuntu@YOUR_SERVER"
port = 22
identity_file = ""
extra_args = []
```

Examples:

```toml
host = "alice@192.168.1.50"
host = "ubuntu@ec2-203-0-113-10.compute-1.amazonaws.com"
host = "root@your-vps.example.com"
```

## Google Compute Engine

Use gcloud mode only if you prefer `gcloud compute ssh` over plain SSH:

```toml
[server]
mode = "gcloud"

[gcloud]
project = "YOUR_GCP_PROJECT_ID"
zone = "YOUR_GCP_ZONE"
instance = "YOUR_GCE_INSTANCE_NAME"
user = ""
tunnel_through_iap = false
```

GCE is an optional convenience mode. The project itself is not Google-specific.
