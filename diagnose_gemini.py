#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot Gemini API connection issues.
Run this before your main script to verify everything is working.
"""

import os
import sys

def check_environment():
    """Check if API key is in environment or prompt user."""
    print("=" * 60)
    print("STEP 1: Checking Environment Variables")
    print("=" * 60)
    
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"✅ GEMINI_API_KEY found in environment")
        print(f"   Length: {len(api_key)} characters")
        print(f"   Ends with: ...{api_key[-4:]}")
        return api_key
    else:
        print("⚠️ GEMINI_API_KEY not found in environment variables")
        print("\n📝 Get your API key at: https://makersuite.google.com/app/apikey")
        print("\n" + "-" * 60)
        
        # Prompt user for API key
        try:
            api_key = input("\nPaste your Gemini API key here: ").strip()
            
            if not api_key:
                print("❌ No API key provided!")
                return None
            
            # Basic validation
            if len(api_key) < 20:
                print("⚠️ Warning: API key seems too short. Are you sure it's correct?")
                confirm = input("Continue anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    return None
            
            print(f"✅ API key received (length: {len(api_key)} characters)")
            print(f"   Ends with: ...{api_key[-4:]}")
            
            # Optionally save to environment for this session
            os.environ['GEMINI_API_KEY'] = api_key
            print("✅ API key set for this session")
            
            return api_key
            
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            return None

def check_installation():
    """Check if required packages are installed."""
    print("\n" + "=" * 60)
    print("STEP 2: Checking Package Installation")
    print("=" * 60)
    
    try:
        import google.generativeai as genai
        print("✅ google-generativeai is installed")
        return True
    except ImportError:
        print("❌ google-generativeai is NOT installed")
        print("\n📦 Install it with:")
        print("    pip install google-generativeai")
        return False

def test_api_connection(api_key):
    """Test actual API connection."""
    print("\n" + "=" * 60)
    print("STEP 3: Testing API Connection")
    print("=" * 60)
    
    try:
        import google.generativeai as genai
        
        # Configure API
        print("Configuring API...")
        genai.configure(api_key=api_key)
        print("✅ API configured")
        
        # List models
        print("\nFetching available models...")
        models = list(genai.list_models())
        print(f"✅ Found {len(models)} models")
        
        # Filter generative models
        generative = [m for m in models if 'generateContent' in m.supported_generation_methods]
        
        if not generative:
            print("❌ No generative models available!")
            return None
        
        print(f"\n📋 Available Generative Models ({len(generative)}):")
        for i, model in enumerate(generative, 1):
            print(f"   {i}. {model.name}")
            print(f"      Display Name: {model.display_name}")
            print(f"      Description: {model.description}")
            print()
        
        return generative[0]
        
    except Exception as e:
        print(f"❌ API connection failed!")
        print(f"   Error: {str(e)}")
        print("\n🔧 Possible issues:")
        print("   - Invalid API key")
        print("   - API key doesn't have access to Gemini models")
        print("   - Network connectivity issues")
        print("   - API quota exceeded")
        return None

def test_generation(model_info):
    """Test actual content generation."""
    print("\n" + "=" * 60)
    print("STEP 4: Testing Content Generation")
    print("=" * 60)
    
    try:
        import google.generativeai as genai
        
        print(f"Using model: {model_info.name}")
        model = genai.GenerativeModel(model_info.name)
        
        print("Generating test content...")
        response = model.generate_content("Say 'Hello World' if you can hear me.")
        
        print("✅ Generation successful!")
        print(f"\nResponse: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Generation failed!")
        print(f"   Error: {str(e)}")
        return False

def main():
    """Run all diagnostic checks."""
    print("\n🔍 GEMINI API DIAGNOSTIC TOOL\n")
    
    # Check 1: Environment
    api_key = check_environment()
    if not api_key:
        print("\n❌ DIAGNOSIS: Missing API key")
        print("   Get your key at: https://makersuite.google.com/app/apikey")
        return False
    
    # Check 2: Installation
    if not check_installation():
        print("\n❌ DIAGNOSIS: Missing package")
        return False
    
    # Check 3: API Connection
    model_info = test_api_connection(api_key)
    if not model_info:
        print("\n❌ DIAGNOSIS: Cannot connect to Gemini API")
        return False
    
    # Check 4: Generation
    if not test_generation(model_info):
        print("\n❌ DIAGNOSIS: Cannot generate content")
        return False
    
    # Success!
    print("\n" + "=" * 60)
    print("✅ ALL CHECKS PASSED!")
    print("=" * 60)
    print("\nYour Gemini API setup is working correctly.")
    print("You can now run your main script.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
