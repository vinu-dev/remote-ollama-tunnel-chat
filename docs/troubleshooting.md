# Troubleshooting

## Missing `config/config.toml`

Copy the example config:

```bash
cp config/config.example.toml config/config.toml
```

On Windows:

```powershell
Copy-Item .\config\config.example.toml .\config\config.toml
notepad .\config\config.toml
```

## Python Version Error

Use Python 3.11 or newer:

```bash
python --version
```

## Local Mode Fails

Check your local or LAN Ollama URL:

```bash
curl http://localhost:11434/api/tags
```

Then set:

```toml
[server]
mode = "local"
local_ollama_url = "http://localhost:11434"
```

## SSH Mode Fails

Test SSH directly:

```bash
ssh ubuntu@YOUR_SERVER
```

If you need a key:

```toml
[ssh]
identity_file = "C:\\Users\\you\\.ssh\\your_key"
```

Or on Linux/macOS:

```toml
identity_file = "/home/you/.ssh/your_key"
```

## Gcloud Mode Fails

Test `gcloud compute ssh` directly:

```bash
gcloud compute ssh INSTANCE --zone=ZONE --project=PROJECT
```

Then mirror those values in `config/config.toml`.

## Port 11435 Is Already In Use

Change:

```toml
local_ollama_port = 11436
```

The start command opens the UI with the matching endpoint automatically.

## Model Is Too Slow

Use a smaller model first:

```toml
models = ["llama3.2"]
```

CPU-only servers can run local models, but large models will be slow.
