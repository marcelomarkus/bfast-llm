import json
import re
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bfast_llm import BFastLLM

def test_full_pipeline():
    print("--- Starting Full bfast-llm Integration Test ---")
    
    # 1. Create a large dataset (list of dictionaries)
    print("Step 1: Generating a large dataset...")
    large_dataset = [
        {
            "id": i,
            "name": f"User Name {i}",
            "role": "Software Engineer" if i % 2 == 0 else "Product Manager",
            "active": i % 3 != 0,
            "score": i * 1.5,
            "details": f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Details for user {i}."
        }
        for i in range(25)
    ]
    
    # Convert to JSON string (simulating raw tool output)
    raw_json_str = json.dumps(large_dataset)
    print(f"  Raw JSON size: {len(raw_json_str)} characters/tokens")
    
    # 2. Set up initial messages
    messages = [
        {"role": "system", "content": "You are a database assistant."},
        {"role": "user", "content": "Retrieve all users from database."},
        {"role": "tool", "content": raw_json_str, "tool_call_id": "call_db_1"}
    ]
    
    # 3. Initialize BFastLLM middleware (threshold_bytes=100 so our 25 users trigger it)
    print("\nStep 2: Initializing BFastLLM middleware and compressing messages...")
    bfast_llm = BFastLLM(threshold_bytes=100)
    
    compressed_messages, was_compressed = bfast_llm.compress_messages(messages)
    
    assert was_compressed, "Expected message to be compressed"
    
    print("  Compression successful!")
    print("\nModified Tool Message Content:")
    tool_msg_content = compressed_messages[2]["content"]
    print(tool_msg_content)
    
    # 4. Extract ref_id from the tag using regex
    # Tag pattern: <bfast-ref id="bfast_abc123" size="..." summary="..."/>
    ref_match = re.search(r'<bfast-ref id="([^"]+)"', tool_msg_content)
    assert ref_match, "Reference tag not found in tool message content"
    ref_id = ref_match.group(1)
    print(f"\nStep 3: Extracted reference ID: '{ref_id}'")
    
    # Verify the reference exists in the registry
    binary_payload = bfast_llm.registry.get(ref_id)
    assert binary_payload is not None, "Payload not found in registry"
    print(f"  Binary payload retrieved from registry: {len(binary_payload)} bytes")
    
    # 5. Simulate LLM wanting to retrieve the content
    print("\nStep 4: Simulating LLM calling bfast_retrieve tool...")
    
    # Mocking OpenAI tool call object
    class MockFunction:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments
            
    class MockToolCall:
        def __init__(self, function):
            self.function = function
            
    mock_tool_call = MockToolCall(
        function=MockFunction(
            name="bfast_retrieve",
            arguments=json.dumps({"ref_id": ref_id, "format": "markdown"})
        )
    )
    
    # Retrieve using our handler
    retrieved_content = bfast_llm.handle_tool_call(mock_tool_call)
    
    print("\nRetrieved & Formatted Content (Markdown):")
    print("\n".join(retrieved_content.split("\n")[:10]))  # Print first 10 lines
    print("...")
    print("\n".join(retrieved_content.split("\n")[-3:]))   # Print last 3 lines
    
    # Assertions on formatted output
    assert "### ⚡ B-FAST Payload" in retrieved_content
    assert ref_id in retrieved_content
    assert "| id | name | role | active | score | details |" in retrieved_content
    assert "✅ Yes" in retrieved_content or "❌ No" in retrieved_content
    
    # 6. Test JSON and YAML retrieval formats
    print("\nStep 5: Testing retrieval in alternative formats (JSON & CSV)...")
    json_retrieved = bfast_llm.handle_tool_call(
        MockToolCall(MockFunction("bfast_retrieve", json.dumps({"ref_id": ref_id, "format": "json"})))
    )
    csv_retrieved = bfast_llm.handle_tool_call(
        MockToolCall(MockFunction("bfast_retrieve", json.dumps({"ref_id": ref_id, "format": "csv"})))
    )
    
    assert json_retrieved.strip().startswith("[")
    assert "User Name 0" in json_retrieved
    assert "id,name,role,active,score,details" in csv_retrieved
    
    print("  JSON and CSV formatting successfully verified.")
    print("\n✅ All integration pipeline checks passed successfully!")

if __name__ == "__main__":
    test_full_pipeline()
