import openai
from dotenv import load_dotenv

load_dotenv()
client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))