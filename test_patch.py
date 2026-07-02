import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bfast_llm import patch_openai

# Mock classes for OpenAI SDK structures
class MockChoiceMessage:
    def __init__(self, role, content, tool_calls=None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls

class MockChoice:
    def __init__(self, message):
        self.message = message

class MockResponse:
    def __init__(self, choices):
        self.choices = choices

class MockToolCallFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class MockToolCall:
    def __init__(self, tc_id, function):
        self.id = tc_id
        self.type = "function"
        self.function = function

class MockCompletions:
    def __init__(self):
        self.call_count = 0
        self.last_messages = []
        self.last_tools = []
        
    def create(self, model, messages, tools=None, **kwargs):
        self.call_count += 1
        self.last_messages = messages
        self.last_tools = tools
        
        if self.call_count == 1:
            # First call: extract ref_id and simulate tool call to bfast_retrieve
            tool_msg = messages[-1]["content"]
            # Find bfast_ref tag
            import re
            match = re.search(r'<bfast-ref id="([^"]+)"', tool_msg)
            ref_id = match.group(1) if match else "bfast_mocked"
            
            # Simulate LLM returning tool call to retrieve the payload
            func = MockToolCallFunction("bfast_retrieve", json.dumps({"ref_id": ref_id}))
            tool_call = MockToolCall("call_retrieve_123", func)
            
            return MockResponse([
                MockChoice(
                    MockChoiceMessage(
                        role="assistant",
                        content=None,
                        tool_calls=[tool_call]
                    )
                )
            ])
        else:
            # Second call: LLM has the decoded markdown table, return final answer
            return MockResponse([
                MockChoice(
                    MockChoiceMessage(
                        role="assistant",
                        content="Here is the analysis of the users: most of them are Engineers."
                    )
                )
            ])

class MockOpenAIClient:
    def __init__(self):
        class CompletionsWrapper:
            def __init__(self):
                self.completions = MockCompletions()
        self.chat = CompletionsWrapper()

def test_patched_client():
    print("--- Testing patch_openai wrapper ---")
    client = MockOpenAIClient()
    
    # Apply patch_openai to the mock client
    patched_client = patch_openai(client, threshold_bytes=100)
    
    # Setup messages with large JSON payload
    large_payload = [{"id": i, "name": f"User {i}", "role": "Engineer"} for i in range(20)]
    messages = [
        {"role": "system", "content": "You are a data assistant."},
        {"role": "user", "content": "Analyze these users:"},
        {"role": "tool", "content": json.dumps(large_payload), "tool_call_id": "call_db_1"}
    ]
    
    print("Making patched completion call...")
    response = patched_client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    
    print("\nFinal response:")
    print(response.choices[0].message.content)
    
    # Assertions
    # The completions.create should have been called twice (once for tool call, once for final result)
    assert client.chat.completions.call_count == 2
    
    # Verify messages list on final call
    final_messages = client.chat.completions.last_messages
    assert len(final_messages) == 5
    
    # 1. System, 2. User, 3. Compressed tool response, 4. Assistant tool call, 5. Tool response with markdown
    assert "bfast-ref" in final_messages[2]["content"]
    assert final_messages[3].tool_calls[0].function.name == "bfast_retrieve"
    assert final_messages[4]["role"] == "tool"
    assert "| id | name | role |" in final_messages[4]["content"]
    
    print("\n✅ patch_openai completely verified! No boilerplate code, 100% plug & play.")


def test_numpy_client():
    import numpy as np
    print("\n--- Testing NumPy array patch_openai support ---")
    client = MockOpenAIClient()
    patched_client = patch_openai(client, threshold_bytes=50)
    
    # Large NumPy array
    array = np.array([1.5, 2.7, 3.9, 4.1, 5.3, 6.8] * 10)
    messages = [
        {"role": "user", "content": "Here is the dataset:"},
        {"role": "tool", "content": array, "tool_call_id": "call_numpy_1"}
    ]
    
    response = patched_client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    
    print("\nNumPy response:")
    print(response.choices[0].message.content)
    
    # Assertions
    assert client.chat.completions.call_count == 2
    final_messages = client.chat.completions.last_messages
    assert "bfast-ref" in final_messages[1]["content"]
    assert "Stats: min=1.5000" in final_messages[1]["content"]
    
    print("✅ NumPy support verified successfully!")


if __name__ == "__main__":
    test_patched_client()
    test_numpy_client()
