import os
import json
import sys
import asyncio
from typing import Any, Dict, List, Optional
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import uvicorn

from .middleware import BFastLLM

app = FastAPI(title="B-FAST LLM Plug-and-Play Proxy")

# Configurable upstream settings
UPSTREAM_API_BASE = os.environ.get("UPSTREAM_API_BASE", "https://api.openai.com/v1")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8787"))
THRESHOLD_BYTES = int(os.environ.get("THRESHOLD_BYTES", "1024"))

# Instantiate the global middleware
bfast_llm = BFastLLM(threshold_bytes=THRESHOLD_BYTES)

async def mock_stream_response(final_response: Dict[str, Any]):
    """Simulate a streaming SSE response from a static ChatCompletion response."""
    resp_id = final_response.get("id", "chatcmpl-mock")
    model = final_response.get("model", "gpt-4")
    choices = final_response.get("choices", [])
    if not choices:
        yield "data: [DONE]\n\n"
        return
        
    content = choices[0].get("message", {}).get("content", "")
    
    # Send initial chunk
    chunk = {
        "id": resp_id,
        "object": "chat.completion.chunk",
        "created": final_response.get("created", 0),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant"},
            "finish_reason": None
        }]
    }
    yield f"data: {json.dumps(chunk)}\n\n"
    await asyncio.sleep(0.01)
    
    # Split content and stream it in small chunks
    chunk_size = 8
    for i in range(0, len(content), chunk_size):
        part = content[i:i+chunk_size]
        chunk = {
            "id": resp_id,
            "object": "chat.completion.chunk",
            "created": final_response.get("created", 0),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": part},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.005)
        
    # Send final chunk
    chunk = {
        "id": resp_id,
        "object": "chat.completion.chunk",
        "created": final_response.get("created", 0),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(chunk)}\n\n"
    await asyncio.sleep(0.001)
    yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    # Parse incoming request body
    body_bytes = await request.body()
    try:
        body_dict = json.loads(body_bytes)
    except json.JSONDecodeError:
        return Response(content="Invalid JSON body", status_code=400)
        
    # Extract headers (forward all auth and content headers)
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "accept-encoding")
    }
    
    # Check if streaming is requested
    client_wants_stream = body_dict.get("stream", False)
    
    # Copy payload to mutate it
    current_payload = body_dict.copy()
    
    async with httpx.AsyncClient() as client:
        while True:
            # Apply prompt compression
            messages = current_payload.get("messages", [])
            compressed_messages, was_compressed = bfast_llm.compress_messages(messages)
            current_payload["messages"] = compressed_messages
            
            # If we compressed the payload, inject our retrieval tool
            if was_compressed:
                tools = current_payload.get("tools", [])
                has_tool = any(t.get("function", {}).get("name") == "bfast_retrieve" for t in tools)
                if not has_tool:
                    tools = list(tools) + bfast_llm.get_tools()
                    current_payload["tools"] = tools
                    
                    # Ensure tool_choice is set to auto or left alone
                    if "tool_choice" not in current_payload:
                        current_payload["tool_choice"] = "auto"
            
            # If the payload was compressed, we MUST use non-streaming to intercept the retrieval loop
            if was_compressed and client_wants_stream:
                current_payload["stream"] = False
                
            # Forward the request to the upstream API
            upstream_url = f"{UPSTREAM_API_BASE}/chat/completions"
            print(f"[Proxy] Forwarding request to {upstream_url} (compressed={was_compressed})...")
            
            try:
                response = await client.post(
                    upstream_url,
                    json=current_payload,
                    headers=headers,
                    timeout=120.0
                )
            except Exception as e:
                return Response(content=f"Upstream request failed: {e}", status_code=502)
                
            if response.status_code != 200:
                print(f"[Proxy] Upstream returned error status {response.status_code}: {response.text}")
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
            # If client requested stream and we did NOT compress, we can forward the stream directly
            if client_wants_stream and not was_compressed:
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
            # Otherwise, read the full JSON response
            response_json = response.json()
            choices = response_json.get("choices", [])
            if not choices:
                return response_json
                
            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            # Check for retrieval calls
            bfast_calls = [tc for tc in tool_calls if tc.get("function", {}).get("name") == "bfast_retrieve"]
            
            if not bfast_calls:
                # No retrieve tool calls. This is the final response.
                if client_wants_stream and was_compressed:
                    # Simulated stream for compressed responses
                    print("[Proxy] Generating simulated stream response...")
                    return StreamingResponse(
                        mock_stream_response(response_json),
                        media_type="text/event-stream"
                    )
                # Standard response
                return response_json
                
            # Handle tool calls locally
            print(f"[Proxy] Intercepting bfast_retrieve tool calls: {len(bfast_calls)}")
            
            # Append assistant's tool call message
            compressed_messages.append(message)
            
            for tool_call in bfast_calls:
                # Retrieve from local BFast registry
                result = bfast_llm.handle_tool_call(tool_call)
                
                # Append tool result message
                compressed_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": "bfast_retrieve",
                    "content": result
                })
                
            # Update payload and loop back to send tool responses to the model
            current_payload["messages"] = compressed_messages


# Standard fallback route to forward all other requests (models, list, etc.)
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def wildcard(request: Request, path: str):
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "accept-encoding")
    }
    body = await request.body()
    upstream_url = f"{UPSTREAM_API_BASE}/{path}"
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=upstream_url,
            content=body,
            headers=headers,
            timeout=30.0
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )

def main():
    print("=" * 60)
    print(f"⚡ B-FAST LLM Proxy running on http://localhost:{PROXY_PORT}")
    print(f"⚡ Upstream target: {UPSTREAM_API_BASE}")
    print(f"⚡ Compression threshold: {THRESHOLD_BYTES} bytes")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT)

if __name__ == "__main__":
    main()
