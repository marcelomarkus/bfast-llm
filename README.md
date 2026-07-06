# ⚡ B-FAST LLM (bfast-llm)

*Documentation: [English](#english) | [Português](#português)*

---

## English

**bfast-llm** is an open-source, local-first context compression layer for Large Language Models (LLMs). It intercepts massive structures, tool outputs, and document contents in your LLM prompts, compressing them using the ultra-high performance [B-FAST](https://github.com/marcelomarkus/b-fast) binary protocol.

If the LLM decides it needs to read the detailed payload to answer a user's question, it uses bfast-llm. The middleware intercepts this call, decodes the binary block locally using the high-performance B-FAST decoder, and returns it to the LLM.

![B-FAST LLM Proxy](assets/screenshot.png)


### 🚀 Key Features

*   **Content-Compressed Retrieval (CCR):** Drastically reduces prompt token consumption transparently, preserving the model's reasoning capabilities.
*   **High-Performance B-FAST Decoder:** Fast and efficient native decoding of compressed binary structures.
*   **Smart Structure Summarization:** Allows the LLM to understand the high-level data structure and schema without reading the raw payload.
*   **Registry and Deduplication:** Avoids redundant processing of identical payloads in the conversation history via unique content identification.
*   **Flexible Caching:** Optimized storage of binary payloads in-memory or on-disk.

### 📦 Installation

Install `bfast-llm` using [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv add bfast-llm
```

Or install it via traditional `pip`:

```bash
pip install bfast-llm
```

### 🔌 Plug & Play Proxy Mode (Zero Code Changes)

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
   *Now, any script, LangChain agent, or developer assistant running in this terminal will have its prompt contexts compressed automatically and transparently!*

### 🛠️ Usage Example (One-Liner Integration)

`bfast-llm` provides a simple drop-in wrapper for the OpenAI client. It automatically handles prompt compression, registers the retrieval tool, and resolves retrieval requests transparently.

```python
import json
from openai import OpenAI
from bfast_llm import bfast_tune

# 1. Initialize client and apply patch
client = bfast_tune(OpenAI(api_key="your-api-key"), threshold_bytes=1024)

# 2. Setup messages containing a large payload
large_query_output = [
    {"id": i, "name": f"User {i}", "role": "Engineer", "active": True}
    for i in range(100)
]

messages = [
    {"role": "system", "content": "You are a helpful data analyst."},
    {"role": "user", "content": "Analyze the query results."},
    {"role": "tool", "content": json.dumps(large_query_output), "tool_call_id": "call_db_1"}
]

# 3. Call the API normally! Prompt compression and retrieval loop are handled transparently!
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)

print(response.choices[0].message.content)
```

> 💡 **What is `threshold_bytes`?**  
> Defines the minimum size (in bytes) a JSON or data structure must be to trigger compression. Structures smaller than this limit (default is `1024` bytes / 1 KB) are sent as raw text to the LLM, as small payloads do not benefit.


---

## Português

O **bfast-llm** é uma camada de compressão de contexto local-first para Modelos de Linguagem de Grande Porte (LLMs). Ele intercepta estruturas massivas, saídas de ferramentas e conteúdos de documentos em seus prompts de LLM, compactando-os utilizando o protocolo binário de altíssimo desempenho [B-FAST](https://github.com/marcelomarkus/b-fast)

Se o LLM decidir que precisa ler a carga detalhada para responder à pergunta de um usuário, ele usa o bfast-llm. O middleware intercepta essa chamada, decodifica o bloco binário localmente usando o decodificador B-FAST de alta performance e devolve ao LLM.

![B-FAST LLM Proxy](assets/screenshot.png)


### 🚀 Funcionalidades Principais

*   **Content-Compressed Retrieval (CCR):** Reduz drasticamente o consumo de tokens em prompts de forma transparente, mantendo a capacidade de raciocínio do modelo.
*   **Decodificador B-FAST de Alta Performance:** Processamento veloz e eficiente de estruturas binárias compactadas nativamente.
*   **Resumos Inteligentes de Estrutura:** Permite ao LLM identificar a estrutura geral e o esquema dos dados sem precisar ler a carga de dados bruta.
*   **Registro e Deduplicação:** Evita o processamento repetitivo de dados idênticos no histórico da conversa por meio de identificação única.
*   **Armazenamento Flexível:** Suporta persistência otimizada dos dados em memória ou em disco.

### 📦 Instalação

Instale o `bfast-llm` usando o [uv](https://github.com/astral-sh/uv) (recomendado):

```bash
uv add bfast-llm
```

Ou instale-o via `pip` tradicional:

```bash
pip install bfast-llm
```

### 🔌 Modo Proxy Plug & Play (Zero Alterações de Código)

Se você não quer alterar nenhuma linha de código da sua aplicação (ou se estiver utilizando ferramentas prontas como Aider, Cursor, LangChain ou agentes pré-existentes), você pode rodar o `bfast-llm` como um proxy HTTP local.

1. **Inicie o Servidor Proxy:**
   ```bash
   bfast-llm-proxy
   ```
   *Isso inicia o servidor local em `http://localhost:8787` direcionado à API da OpenAI por padrão.*

2. **Configure o Upstream e a Porta (Opcional):**
   ```bash
   export UPSTREAM_API_BASE=https://api.openai.com/v1
   export PROXY_PORT=8787
   export THRESHOLD_BYTES=1024
   bfast-llm-proxy
   ```

3. **Direcione seu Agente para o Proxy:**
   Basta definir a variável de ambiente `OPENAI_BASE_URL`:
   ```bash
   export OPENAI_BASE_URL=http://localhost:8787/v1
   ```
   *A partir de agora, qualquer script, framework ou assistente rodando nesse terminal terá seus contextos de prompt comprimidos automaticamente de forma 100% transparente!*

### 🛠️ Como Usar (Integração em Uma Linha)

O `bfast-llm` fornece um wrapper extremamente simples para o cliente da OpenAI. Ele gerencia a compressão de prompts, registra a ferramenta de recuperação e resolve as chamadas de ferramentas de forma 100% transparente.

```python
import json
from openai import OpenAI
from bfast_llm import bfast_tune

# 1. Inicializar o cliente da OpenAI e aplicar o patch
client = bfast_tune(OpenAI(api_key="sua-chave-api"), threshold_bytes=1024)

# 2. Configurar os dados simulando retorno do banco de dados
dados_banco = [
    {"id": i, "name": f"Usuario {i}", "role": "Engenheiro", "active": i % 2 == 0}
    for i in range(150)
]

messages = [
    {"role": "system", "content": "Você é um assistente de análise de dados."},
    {"role": "user", "content": "Gere um relatório sobre os usuários da consulta anterior."},
    {"role": "tool", "content": json.dumps(dados_banco), "tool_call_id": "call_db_query_1"}
]

# 3. Chame a API normalmente! A compressão e o loop de recuperação são tratados de forma transparente!
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)

print(response.choices[0].message.content)
```

> 💡 **O que é o `threshold_bytes`?**  
> Define o tamanho mínimo (em bytes) que um JSON ou estrutura de dados precisa ter para ser compactado. Estruturas menores que esse limite (o padrão é `1024` bytes / 1 KB) são enviadas como texto comum para o LLM, pois dados muito pequenos não compensam.


---

## 📄 License / Licença
Distributed under the MIT License. Veja `LICENSE` para mais detalhes.
