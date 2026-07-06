# Getting Started

Learn how to install, configure, and run `bfast-llm`.

---

## 📦 Installation

Install `bfast-llm` using [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv add bfast-llm
```

Or install it via traditional `pip`:

```bash
pip install bfast-llm
```

---

## 🔌 Plug & Play Proxy Mode (Zero Code Changes)

If you don't want to change any code in your application (or if you are using existing developer tools like Aider, Cursor, LangChain, or custom agents), you can run `bfast-llm` as a local HTTP proxy server.

1. **Start the Proxy Server:**
   ```bash
   bfast-llm-proxy
   ```
   *This starts a local server on `http://localhost:8787` pointing to OpenAI's API by default.*

2. **Configure Upstream & Port (Optional):**
   ```bash
   export UPSTREAM_API_BASE=https://api.openai.com/v1
   export PROXY_PORT=8787
   export THRESHOLD_BYTES=1024
   bfast-llm-proxy
   ```

3. **Redirect your Agent to the Proxy:**
   Simply set the `OPENAI_BASE_URL` environment variable:
   ```bash
   export OPENAI_BASE_URL=http://localhost:8787/v1
   ```

---

## 🛠️ Usage Example (One-Liner Integration)

`bfast-llm` provides a simple drop-in wrapper for the OpenAI client. It automatically handles prompt compression, registers the retrieval tool, and resolves retrieval requests transparently.

```python
import json
from openai import OpenAI
from bfast_llm import bfast_tune

# 1. Initialize client and apply patch
client = bfast_tune(OpenAI(api_key="your-api-key"), threshold_bytes=1024)

# 2. Setup messages containing a large payload
large_payload = [{"id": i, "name": f"User {i}", "data": [i * 2]} for i in range(100)]

messages = [
    {"role": "system", "content": "You are a helpful data assistant."},
    {"role": "user", "content": f"Analyze this user data: {json.dumps(large_payload)}"}
]

# 3. Call the model (Prompt is automatically compressed, and the retrieve tool is injected)
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)

print(response.choices[0].message.content)
```

> 💡 **What is `threshold_bytes`?**  
> Defines the minimum size (in bytes) a JSON or data structure must be to trigger compression. Structures smaller than this limit (default is `1024` bytes / 1 KB) are sent as raw text to the LLM, as small payloads do not benefit.
