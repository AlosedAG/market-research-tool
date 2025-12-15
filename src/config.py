# src/config.py
import os
import google.generativeai as genai

def setup_api_key():
    """Setup Gemini API key from environment variable or user input."""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("\n⚠️ GEMINI_API_KEY not found in environment variables")
        print("Get your API key first.")
        print("-" * 60)
        
        try:
            api_key = input("\nPaste your Gemini API key here: ").strip()
            
            if not api_key:
                raise ValueError("No API key provided")
            
            # Basic validation
            if len(api_key) < 20:
                print("⚠️ Warning: API key seems too short")
                confirm = input("Continue anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    raise ValueError("API key rejected by user")
            
            # Set for this session
            os.environ['GEMINI_API_KEY'] = api_key
            print("✅ API key set for this session")
            
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            raise ValueError("API key input cancelled")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            raise ValueError("Failed to setup API key")
    
    genai.configure(api_key=api_key)
    print(f"✅ API key configured (ends with: ...{api_key[-4:]})")
    return api_key

def get_working_model():
    """Find and return a working Gemini model."""
    
    # List of models to try in order of preference
    preferred_models = [
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro',
        'gemini-1.0-pro'
    ]
    
    try:
        # List all available models
        print("🔍Checking available models...")
        available_models = genai.list_models()
        
        # Filter for generative models
        generative_models = [
            m for m in available_models 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        if not generative_models:
            raise Exception("No generative models available with your API key")
        
        print(f"📋 Found {len(generative_models)} generative models:")
        for model in generative_models:
            print(f"   - {model.name}")
        
        # Try preferred models first
        for preferred in preferred_models:
            for model in generative_models:
                if preferred in model.name:
                    print(f"✅ Selected model: {model.name}")
                    return genai.GenerativeModel(model.name)
        
        # If no preferred model found, use the first available
        selected = generative_models[0]
        print(f"⚠️ No preferred model found, using: {selected.name}")
        return genai.GenerativeModel(selected.name)
        
    except Exception as e:
        print(f"❌ Error accessing Gemini API: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Verify your API key is correct")
        print("2. Check if your API key has access to Gemini models")
        print("3. Visit https://makersuite.google.com/app/apikey to manage keys")
        print("4. Ensure you've enabled the Gemini API in Google Cloud Console")
        raise Exception("Could not find a working Gemini model. Please check your API key and available models.")

def test_model_connection(model):
    """Test if the model can generate content."""
    try:
        print("\nTesting model connection...")
        response = model.generate_content("Say 'Hello' if you can hear me.")
        print(f"✅ Model test successful: {response.text[:50]}")
        return True
    except Exception as e:
        print(f"❌ Model test failed: {str(e)}")
        return False

# Diagnostic function
def diagnose_api_setup():
    """Run comprehensive diagnostics on API setup."""
    print("=" * 60)
    print("GEMINI API DIAGNOSTICS")
    print("=" * 60)
    
    # Step 1: Check API key
    print("\n1️Checking API Key...")
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"   ✅ API key found (length: {len(api_key)}, ends with: ...{api_key[-4:]})")
    else:
        print("   ❌ API key NOT found in environment variables")
        return False
    
    # Step 2: Configure API
    print("\n2️Configuring Gemini API...")
    try:
        genai.configure(api_key=api_key)
        print("   ✅ API configured successfully")
    except Exception as e:
        print(f"   ❌ Configuration failed: {str(e)}")
        return False
    
    # Step 3: List models
    print("\n3️Listing Available Models...")
    try:
        models = list(genai.list_models())
        print(f"   ✅ Found {len(models)} total models")
        
        generative = [m for m in models if 'generateContent' in m.supported_generation_methods]
        print(f"   ✅ Found {len(generative)} generative models:")
        for m in generative:
            print(f"      - {m.name}")
    except Exception as e:
        print(f"   ❌ Failed to list models: {str(e)}")
        return False
    
    # Step 4: Test a model
    print("\n4️Testing Model Generation...")
    try:
        model = get_working_model()
        test_model_connection(model)
        print("   ✅ Model is working correctly")
    except Exception as e:
        print(f"   ❌ Model test failed: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL DIAGNOSTICS PASSED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    # Run diagnostics when executed directly
    diagnose_api_setup()
