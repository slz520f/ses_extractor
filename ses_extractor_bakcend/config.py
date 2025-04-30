import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
    GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"