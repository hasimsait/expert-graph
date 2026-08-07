import sys
import os
import json
import asyncio
from openai import OpenAI
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.module_c_mcp.mcp_server import retrieve_verified_facts

logger = logging.getLogger(__name__)

# 1. Define MCP Tool Schema for Llama / OpenAI completion
TOOLS = [
    #hinting the default test case to force tiny models to call the tool
    {
        "type": "function",
        "function": {
            "name": "retrieve_verified_facts",
            "description": "Retrieves human-verified ground truth facts from the ExpertGraph database for a search query. Pass query with relevant topic terms (e.g. query='breast cancer', query='HER2', query='mutation', query='ALL').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or concept topic to retrieve ground truth facts for (e.g. 'breast cancer', 'HER2', 'mutation', 'ALL')"
                    }
                }
            }
        }
    }
]

def ask_llama_with_mcp(user_question: str):
    print("\n=======================================================")
    print("  ASKING LLAMA WITH EXPERTGRAPH MCP TOOL PROVIDER")
    print("=======================================================\n")
    
    base_url = settings.LLM_BASE_URL if settings.LLM_PROVIDER.lower() != "openai" else None
    api_key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else "local"
    model = settings.LLM_MODEL
    
    print(f"--> LLM Model:    {model}")
    print(f"--> Endpoint:     {base_url or 'OpenAI Cloud'}")
    print(f"--> User Prompt:  \"{user_question}\"\n")

    client = OpenAI(base_url=base_url, api_key=api_key)
    
    messages = [
        {
            "role": "system", 
            "content": "You are an expert AI assistant. Always use the retrieve_verified_facts tool with specific search query terms to query ground-truth facts from ExpertGraph before answering. Synthesize a clear answer based strictly on the retrieved facts and include the mcp-ui presentation widget URL."
        },
        {"role": "user", "content": user_question}
    ]

    try:
        # Step 1: Hit LLM with question + MCP tool definition
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=settings.MAX_TOKENS,
            stop=settings.get_stop_tokens()
        )
        
        message = response.choices[0].message
        
        # Step 2: Check standard OpenAI tool calls or text-based Qwen/Gemma tool calls
        tool_calls_to_process = []
        if message.tool_calls:
            for tc in message.tool_calls:
                raw_args = tc.function.arguments
                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                tool_calls_to_process.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": parsed_args
                })
        elif message.content and ("retrieve_verified_facts" in message.content):
            import re
            logger.info("Detected text-based tool call in response content.")
            args_dict = {"query": user_question}
            match = re.search(r'call:retrieve_verified_facts\s*\{([^}]+)\}', message.content)
            if match:
                raw_args = match.group(1)
                q_match = re.search(r'(?:query|concept)\s*:\s*"([^"]+)"', raw_args)
                if q_match:
                    args_dict["query"] = q_match.group(1)
            tool_calls_to_process.append({
                "id": "text_tool_call_1",
                "name": "retrieve_verified_facts",
                "args": args_dict
            })

        if tool_calls_to_process:
            for tool_call in tool_calls_to_process:
                func_name = tool_call["name"]
                func_args = tool_call["args"]
                print(f"--> LLM invoked MCP Tool: '{func_name}' with args: {func_args}")
                
                if func_name == "retrieve_verified_facts":
                    query_val = func_args.get("query") or user_question
                    
                    # Step 3: Execute ExpertGraph MCP Tool
                    tool_output = asyncio.run(retrieve_verified_facts(query=query_val))
                    print(f"\n<-- ExpertGraph MCP Tool Output:\n{tool_output}\n")
                    
                    # Append tool result back to message history
                    messages.append(message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_output
                    })
            
            # Step 4: Get LLM's final answer using verified ground truth
            final_response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=settings.MAX_TOKENS,
                stop=settings.get_stop_tokens()
            )
            final_answer = final_response.choices[0].message.content
            print("=======================================================")
            print("  LLM'S FINAL VERIFIED ANSWER")
            print("=======================================================")
            print(final_answer)
            print("=======================================================\n")
        else:
            print("Llama Direct Answer (no tool call requested):")
            print(message.content)

    except Exception as e:
        print(f"Error querying Llama endpoint ({base_url}): {e}")

if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "What genetic mutations were identified in breast cancer tissue samples?"
    ask_llama_with_mcp(question)
