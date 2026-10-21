import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

model_config = {
    "model": os.getenv("LLM_MODEL", "deepseek-chat"),
    "api_key": os.getenv("OPENAI_API_KEY"),
    "temperature": 0.2,
    "extra_body": {"thinking": {"type": "disabled"}}
}

base_url = os.getenv("OPENAI_BASE_URL")
if  base_url:
    model_config["base_url"] = base_url

llm = ChatOpenAI(**model_config)