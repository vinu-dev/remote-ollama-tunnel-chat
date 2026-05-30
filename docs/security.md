# Security

This project is designed around one safe default:

```text
Do not expose Ollama directly to the public internet.
```

For remote installs, the installer configures:

```text
OLLAMA_HOST=127.0.0.1:11434
```

That means Ollama listens only on the server's loopback interface. The start command then creates a local SSH tunnel from your computer to that loopback address.

## Keep Out of Git

Never commit:

- `config/config.toml`
- service account JSON files
- SSH private keys
- API keys
- cloud credentials
- passwords

The `.gitignore` excludes common local config and credential patterns, but you should still scan before publishing.

## Stop Command Behavior

`scripts/remote_ollama_chat.py stop` only stops local helper processes recorded in `.runtime/`.

It does not:

- stop a VM
- reboot a server
- delete an instance
- change firewall rules
- remove models

## Public Repositories

Before publishing your own fork, run:

```bash
rg -n "PROJECT_ID|YOUR_|service_account|private_key|BEGIN .*PRIVATE KEY|password|token|secret" .
```
