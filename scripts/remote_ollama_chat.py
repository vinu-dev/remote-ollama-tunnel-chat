#!/usr/bin/env python3
"""Start a tiny Ollama chat UI for local or tunneled remote servers."""

from __future__ import annotations

import argparse
import base64
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    print("Python 3.11 or newer is required for TOML config parsing.", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.toml"
RUNTIME_DIR = ROOT / ".runtime"
UI_DIR = ROOT / "ui"


class ConfigError(RuntimeError):
    pass


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise ConfigError(
            "Missing config/config.toml. Copy config/config.example.toml to config/config.toml and edit it."
        )

    with CONFIG_PATH.open("rb") as handle:
        config = tomllib.load(handle)

    server = config.setdefault("server", {})
    server.setdefault("mode", "ssh")
    server.setdefault("local_ollama_url", "http://localhost:11434")
    server.setdefault("remote_ollama_host", "127.0.0.1")
    server.setdefault("remote_ollama_port", 11434)
    server.setdefault("local_ollama_port", 11435)
    server.setdefault("local_ui_port", 8787)

    config.setdefault("ssh", {})
    config["ssh"].setdefault("host", "")
    config["ssh"].setdefault("port", 22)
    config["ssh"].setdefault("identity_file", "")
    config["ssh"].setdefault("extra_args", [])

    config.setdefault("gcloud", {})
    config["gcloud"].setdefault("project", "")
    config["gcloud"].setdefault("zone", "")
    config["gcloud"].setdefault("instance", "")
    config["gcloud"].setdefault("user", "")
    config["gcloud"].setdefault("tunnel_through_iap", False)

    config.setdefault("install", {})
    config["install"].setdefault("remote_install_root", "/opt/remote-ollama-tunnel-chat")
    config["install"].setdefault("models", ["llama3.2"])

    mode = str(server["mode"]).lower()
    if mode not in {"local", "ssh", "gcloud"}:
        raise ConfigError('server.mode must be "local", "ssh", or "gcloud".')
    server["mode"] = mode

    if mode == "ssh" and not config["ssh"]["host"]:
        raise ConfigError("Set ssh.host in config/config.toml, or change server.mode.")

    if mode == "gcloud":
        for key in ("project", "zone", "instance"):
            value = str(config["gcloud"].get(key, ""))
            if not value or value.startswith("YOUR_"):
                raise ConfigError(f"Set gcloud.{key} in config/config.toml.")

    return config


def tool(name: str) -> str:
    if os.name == "nt" and name == "gcloud":
        found = shutil.which("gcloud.cmd") or shutil.which("gcloud")
    else:
        found = shutil.which(name)
    if not found:
        raise ConfigError(f"{name} was not found on PATH.")
    return found


def tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError):
        return False


def wait_http(url: str, seconds: int) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if http_ok(url):
            return True
        time.sleep(0.6)
    return False


def hidden_popen(args: list[str]) -> subprocess.Popen:
    kwargs = {
        "cwd": str(ROOT),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(args, **kwargs)


def pid_path(name: str) -> Path:
    RUNTIME_DIR.mkdir(exist_ok=True)
    return RUNTIME_DIR / f"{name}.pid"


def write_pid(name: str, process: subprocess.Popen) -> None:
    pid_path(name).write_text(str(process.pid), encoding="utf-8")


def read_pid(name: str) -> int | None:
    path = pid_path(name)
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def kill_pid(name: str) -> None:
    pid = read_pid(name)
    path = pid_path(name)
    if not pid:
        print(f"No {name} process recorded.")
        return

    print(f"Stopping {name} process PID {pid}")
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    path.unlink(missing_ok=True)


def api_base(config: dict) -> str:
    server = config["server"]
    if server["mode"] == "local":
        return str(server["local_ollama_url"]).rstrip("/")
    return f"http://localhost:{int(server['local_ollama_port'])}"


def ssh_base_args(config: dict) -> list[str]:
    ssh = config["ssh"]
    args = [tool("ssh")]
    if ssh.get("port"):
        args += ["-p", str(ssh["port"])]
    if ssh.get("identity_file"):
        args += ["-i", str(ssh["identity_file"])]
    args += [str(item) for item in ssh.get("extra_args", [])]
    return args


def gcloud_base_args(config: dict) -> list[str]:
    cloud = config["gcloud"]
    target = cloud["instance"]
    if cloud.get("user"):
        target = f"{cloud['user']}@{target}"

    args = [
        tool("gcloud"),
        "compute",
        "ssh",
        target,
        f"--zone={cloud['zone']}",
        f"--project={cloud['project']}",
    ]
    if cloud.get("tunnel_through_iap"):
        args.append("--tunnel-through-iap")
    return args


def tunnel_command(config: dict) -> list[str]:
    server = config["server"]
    tunnel = (
        f"{int(server['local_ollama_port'])}:"
        f"{server['remote_ollama_host']}:"
        f"{int(server['remote_ollama_port'])}"
    )

    if server["mode"] == "ssh":
        return ssh_base_args(config) + ["-N", "-L", tunnel, config["ssh"]["host"]]
    if server["mode"] == "gcloud":
        return gcloud_base_args(config) + ["--", "-N", "-L", tunnel]
    raise ConfigError("Local mode does not use an SSH tunnel.")


def remote_exec_command(config: dict, remote_command: str) -> list[str]:
    mode = config["server"]["mode"]
    if mode == "ssh":
        return ssh_base_args(config) + [config["ssh"]["host"], remote_command]
    if mode == "gcloud":
        return gcloud_base_args(config) + [f"--command={remote_command}"]
    raise ConfigError("Install is only available for ssh and gcloud modes.")


def start_tunnel(config: dict) -> None:
    if config["server"]["mode"] == "local":
        return

    base = api_base(config)
    tags_url = f"{base}/api/tags"
    local_port = int(config["server"]["local_ollama_port"])

    if tcp_open("127.0.0.1", local_port):
        if http_ok(tags_url):
            print(f"Ollama tunnel already reachable at {base}")
            return
        raise ConfigError(
            f"Local port {local_port} is already in use, but it does not look like Ollama."
        )

    process = hidden_popen(tunnel_command(config))
    write_pid("tunnel", process)

    if not wait_http(tags_url, 45):
        raise ConfigError(f"Could not reach remote Ollama through {base}")

    print(f"Ollama tunnel: {base}")


def start_ui(config: dict) -> None:
    ui_port = int(config["server"]["local_ui_port"])
    if not tcp_open("127.0.0.1", ui_port):
        process = hidden_popen(
            [sys.executable, "-m", "http.server", str(ui_port), "-d", str(UI_DIR)]
        )
        write_pid("ui", process)
        if not wait_http(f"http://127.0.0.1:{ui_port}/", 10):
            raise ConfigError("The local chat UI server did not start.")

    endpoint = urllib.parse.quote(api_base(config), safe="")
    url = f"http://127.0.0.1:{ui_port}/?endpoint={endpoint}"
    webbrowser.open(url)
    print(f"Chat UI: {url}")


def start(config: dict) -> None:
    base = api_base(config)
    if config["server"]["mode"] == "local" and not http_ok(f"{base}/api/tags"):
        raise ConfigError(f"Ollama is not reachable at {base}")
    start_tunnel(config)
    start_ui(config)


def stop(_: dict | None = None) -> None:
    kill_pid("tunnel")
    kill_pid("ui")
    print("Local chat UI and SSH tunnel stopped.")
    print("No server, VM, or cloud instance was stopped.")


def install(config: dict) -> None:
    if config["server"]["mode"] == "local":
        raise ConfigError("Install is for remote ssh/gcloud Linux targets, not local mode.")

    install_root = str(config["install"]["remote_install_root"])
    models = [str(model).strip() for model in config["install"].get("models", []) if str(model).strip()]

    root_b64 = base64.b64encode(install_root.encode("utf-8")).decode("ascii")
    models_b64 = base64.b64encode("\n".join(models).encode("utf-8")).decode("ascii")

    remote_script = f"""set -euo pipefail
install_root=$(printf '%s' '{root_b64}' | base64 -d)
models_text=$(printf '%s' '{models_b64}' | base64 -d)

if command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y curl ca-certificates zstd
fi

if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

systemctl enable --now ollama
install -d -o root -g root -m 755 "$install_root"
install -d -o ollama -g ollama -m 750 "$install_root/ollama" "$install_root/ollama/models"
install -d -o root -g root -m 755 /etc/systemd/system/ollama.service.d

cat > /etc/systemd/system/ollama.service.d/10-remote-ollama-tunnel-chat.conf <<EOF
[Service]
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_MODELS=$install_root/ollama/models
Environment=OLLAMA_KEEP_ALIVE=5m
Environment=OLLAMA_NUM_PARALLEL=1
EOF

systemctl daemon-reload
systemctl restart ollama
sleep 2

if [ -n "$models_text" ]; then
  while IFS= read -r model; do
    [ -z "$model" ] && continue
    echo "Pulling $model"
    ollama pull "$model"
  done <<EOF
$models_text
EOF
fi

echo
echo "Ollama status:"
systemctl is-active ollama
echo
echo "Installed models:"
ollama list
echo
echo "Model storage:"
du -sh "$install_root/ollama/models" || true
"""
    payload = base64.b64encode(remote_script.encode("utf-8")).decode("ascii")
    remote_command = f"echo {payload} | base64 -d | sudo bash"

    print("Installing Ollama on remote Linux target.")
    subprocess.run(remote_exec_command(config, remote_command), check=True)


def status(config: dict) -> None:
    base = api_base(config)
    print(f"Mode: {config['server']['mode']}")
    print(f"Ollama API: {base}")
    print(f"Chat UI: http://127.0.0.1:{int(config['server']['local_ui_port'])}/")
    print(f"API reachable: {http_ok(f'{base}/api/tags')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Remote/local Ollama tunnel chat helper")
    parser.add_argument("command", choices=["install", "start", "stop", "status"])
    args = parser.parse_args()

    try:
        if args.command == "stop":
            stop()
            return 0

        config = load_config()
        if args.command == "install":
            install(config)
        elif args.command == "start":
            start(config)
        elif args.command == "status":
            status(config)
        return 0
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as error:
        print(f"Command failed with exit code {error.returncode}.", file=sys.stderr)
        return error.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
