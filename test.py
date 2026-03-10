import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv('GROQ_API_KEY')
print(f"API Key found: {api_key is not None}")

if api_key:
    print(f"API Key (first 10 chars): {api_key[:10]}...")
    
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Say hello"}]
        )
        print("SUCCESS: Groq API working!")
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"ERROR: {e}")
else:
    print("ERROR: No API key found")
