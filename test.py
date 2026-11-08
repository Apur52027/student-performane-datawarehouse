
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os

load_dotenv()

try:
    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )

    response = llm.invoke(
        "Say: Groq GPT-OSS-120B is working successfully!"
    )

    print("\nSUCCESS! Model is working.")
    print("Model:", os.getenv("GROQ_MODEL"))
    print("Response:", response.content)

except Exception as e:
    print("\nFAILED! Model is not working.")
    print("Error:", str(e))
