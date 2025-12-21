# src/config.py
import os
import google.generativeai as genai
import logging

logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def setup_api_key():
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        api_key = input("\nPaste your Gemini API key: ").strip()
        if not api_key:
            logging.error("No API key provided")
            raise ValueError("API key is required")  
        os.environ['GEMINI_API_KEY'] = api_key
    
    genai.configure(api_key=api_key)
    logging.info("API key configured successfully")
    return api_key

def get_working_model():
    """
    Fetch all available models from API and let user choose.
    Prioritizes Flash models to save costs.
    """
    try:
        logging.debug("\n→ Fetching available models from API...")
        
        # Get all available models from the API
        all_models = genai.list_models()
        
        # Filter for models that support generateContent
        available_models = []
        for model in all_models:
            # Check if model supports content generation
            if 'generateContent' in model.supported_generation_methods:
                available_models.append({
                    'name': model.name.replace('models/', ''),  # Clean up name
                    'display_name': model.display_name,
                    'description': model.description if hasattr(model, 'description') else 'No description',
                    'input_token_limit': model.input_token_limit if hasattr(model, 'input_token_limit') else 'Unknown'
                })
        
        if not available_models:
            raise Exception("No models available for content generation")
        
        # Sort: Flash models first, then others
        available_models.sort(key=lambda x: (
            'flash' not in x['name'].lower(),  # Flash models first
            x['name']  # Then alphabetically
        ))
        
        # Display models
        print("\n" + "="*70)
        print("AVAILABLE MODELS")
        print("="*70)
        
        for idx, model_info in enumerate(available_models, 1):
            logging.info(f"{idx}. {model_info['name']}")
            logging.info(f"   Display: {model_info['display_name']}")
            logging.info(f"   Input limit: {model_info['input_token_limit']} tokens")
            if idx <= 3:  # Mark recommended models
                logging.info("RECOMMENDED (Cost-effective)")
            print()
        
        # Get user choice
        while True:
            try:
                choice = input(f"Select model (1-{len(available_models)}) or press Enter for default [1]: ").strip()
                
                if choice == "":
                    choice = 1
                else:
                    choice = int(choice)
                
                if 1 <= choice <= len(available_models):
                    break
                else:
                    print(f"Please enter a number between 1 and {len(available_models)}")
            except ValueError:
                logging.error("Please enter a valid number")
        
        # Get selected model
        selected_model = available_models[choice - 1]
        model_name = selected_model['name']
        
        logging.debug(f"\n→ Testing {model_name}...")
        
        # Initialize and test model
        model = genai.GenerativeModel(model_name)
        model.generate_content("Test", generation_config={'max_output_tokens': 1})
        
        logging.info(f"Successfully initialized model: {model_name}")
        logging.info(f"Using model: {model_name}\n")
        return model
        
    except Exception as e:
        logging.error(f"Failed to fetch or initialize models: {e}")
        logging.warning("\nFalling back to default model...")
        
        # Fallback to known good model
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            logging.info("Using fallback model: gemini-1.5-flash")
            logging.warning("Using fallback: gemini-1.5-flash\n")
            return model
        except Exception as fallback_error:
            raise Exception(f"Could not initialize any model: {fallback_error}")