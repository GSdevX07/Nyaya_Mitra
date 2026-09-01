import sys
import os

sys.path.append(os.path.abspath('backend'))

from app.llm_client import generate, get_last_provider, _call_groq

try:
    print(_call_groq("hello", "you are a helpful assistant"))
    print("Direct Groq call succeeded!")
except Exception as e:
    print(f"Direct Groq call failed: {e}")

try:
    res = generate("say hello")
    print(f"Generate output: {res}")
    print(f"Provider used: {get_last_provider()}")
except Exception as e:
    print(f"Generate failed: {e}")
