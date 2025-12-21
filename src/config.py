# src/config.py
import os
import google.generativeai as genai

def setup_api_key():
    """Setup Gemini API key from environment or prompt."""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        api_key = input("\nPaste your Gemini API key: ").strip()
        if not api_key:
            raise ValueError("No API key provided")
        os.environ['GEMINI_API_KEY'] = api_key
    
    genai.configure(api_key=api_key)
    print(f"✅ API key configured")
    return api_key

def get_working_model():
    """Try multiple models to find one that works."""
    model_names = [
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-flash-latest',
        'gemini-1.5-flash'
    ]
    
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            # Quick test
            model.generate_content("Reply: OK", generation_config={'max_output_tokens': 5})
            print(f"✅ Using model: {model_name}")
            return model
        except:
            continue
    
    raise Exception("Could not find a working Gemini model. Check your API key.")