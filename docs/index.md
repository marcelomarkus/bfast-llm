# ⚡ B-FAST LLM (bfast-llm)

![B-FAST LLM Proxy](assets/screenshot.png)

Welcome to the **bfast-llm** documentation.

It intercepts massive structures, tool outputs, and document contents in your LLM prompts, compressing them using the ultra-high performance [B-FAST](https://github.com/marcelomarkus/b-fast) binary protocol.

If the LLM decides it needs to read the detailed payload to answer a user's question, it uses bfast-llm. The middleware intercepts this call, decodes the binary block locally using the high-performance B-FAST decoder, and returns it to the LLM.

---

## 🚀 Key Features

*   **Content-Compressed Retrieval (CCR):** Drastically reduces prompt token consumption transparently, preserving the model's reasoning capabilities.
*   **High-Performance B-FAST Decoder:** Fast and efficient native decoding of compressed binary structures.
*   **Smart Structure Summarization:** Allows the LLM to understand the high-level data structure and schema without reading the raw payload.
*   **Registry and Deduplication:** Avoids redundant processing of identical payloads in the conversation history via unique content identification.
*   **Flexible Caching:** Optimized storage of binary payloads in-memory or on-disk.
