# Model Choices

Default models in `config/config.example.toml`:

```toml
models = [
  "llama3.2",
  "qwen3:8b"
]
```

Suggested choices:

| Model | Best for |
| --- | --- |
| `llama3.2` | Fast tests, short chats, simple summaries. |
| `qwen3:8b` | Better general chat and reasoning on CPU-only servers. |
| `gemma4:latest` | Google's Gemma line, writing, summarization, and long-context experiments. |
| `qwen3-coder:30b` | Coding and debugging, if your server has enough RAM and you can tolerate slower CPU responses. |

For CPU-only servers, avoid installing too many large models at once. Disk use is usually manageable, but response speed depends heavily on CPU and RAM bandwidth.

The chat UI does not hardcode the final list. It asks Ollama for installed models through:

```text
/api/tags
```

So newly pulled models appear after you click Refresh or reload the page.
