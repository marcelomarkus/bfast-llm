# Começando

Aprenda como instalar, configurar e executar o `bfast-llm`.

---

## 📦 Instalação

Instale o `bfast-llm` usando o [uv](https://github.com/astral-sh/uv) (recomendado):

```bash
uv add bfast-llm
```

Ou instale-o via `pip` tradicional:

```bash
pip install bfast-llm
```

---

## 🔌 Modo Proxy Plug & Play (Sem Alterações no Código)

Se você não deseja alterar nenhuma linha de código em sua aplicação (ou se estiver usando ferramentas de desenvolvimento existentes como Aider, Cursor, LangChain ou agentes customizados), você pode executar o `bfast-llm` como um servidor proxy HTTP local.

1. **Inicie o Servidor Proxy:**
   ```bash
   bfast-llm-proxy
   ```
   *Isso inicia um servidor local em `http://localhost:8787` apontando para a API da OpenAI por padrão.*

2. **Configurar Upstream e Porta (Opcional):**
   ```bash
   export UPSTREAM_API_BASE=https://api.openai.com/v1
   export PROXY_PORT=8787
   export THRESHOLD_BYTES=1024
   bfast-llm-proxy
   ```

3. **Redirecionar o seu Agente para o Proxy:**
   Basta definir a variável de ambiente `OPENAI_BASE_URL`:
   ```bash
   export OPENAI_BASE_URL=http://localhost:8787/v1
   ```

---

## 🛠️ Exemplo de Uso (Integração Direta no Código)

O `bfast-llm` fornece um wrapper simples para o cliente OpenAI. Ele lida automaticamente com a compressão de prompts, registra a ferramenta de recuperação (retrieve) e resolve solicitações de recuperação de forma transparente.

```python
import json
from openai import OpenAI
from bfast_llm import bfast_tune

# 1. Inicializar o cliente e aplicar o patch
client = bfast_tune(OpenAI(api_key="sua-chave-api"), threshold_bytes=1024)

# 2. Configurar mensagens contendo uma carga grande
dados_grandes = [{"id": i, "name": f"User {i}", "data": [i * 2]} for i in range(100)]

messages = [
    {"role": "system", "content": "Você é um assistente de dados prestativo."},
    {"role": "user", "content": f"Analise estes dados de usuários: {json.dumps(dados_grandes)}"}
]

# 3. Chamar o modelo (O prompt é comprimido automaticamente e a ferramenta de recuperação é injetada)
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)

print(response.choices[0].message.content)
```

> 💡 **O que é o `threshold_bytes`?**  
> Define o tamanho mínimo (em bytes) que um JSON ou estrutura de dados precisa ter para ser compactado. Estruturas menores que esse limite (o padrão é `1024` bytes / 1 KB) são enviadas como texto comum para o LLM, pois dados muito pequenos não compensam.
