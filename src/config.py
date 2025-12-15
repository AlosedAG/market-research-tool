import os
import google.generativeai as genai
from getpass import getpass

def setup_api_key():
    """Securely handle API Key input."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("--- 🔧 CONFIGURATION ---")
        api_key = getpass("Step 1: Paste your Google Gemini API Key: ")
    
    if api_key:
        genai.configure(api_key=api_key)
        print("✅ API Key loaded.")
    return api_key

def get_working_model():
    """Try multiple model names to find one that works."""
    model_names = [
        'gemini-2.5-flash',           
        'gemini-2.0-flash',            
        'gemini-flash-latest',         
        'gemini-2.5-pro',              
        'gemini-2.5-pro-preview-03-25' 
    ]

    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            # Test with a simple prompt
            model.generate_content("Reply with just: OK")
            print(f"   ✅ Using model: {model_name}")
            return model
        except Exception:
            continue

    raise Exception("Could not find a working Gemini model. Please check your API key and available models.")