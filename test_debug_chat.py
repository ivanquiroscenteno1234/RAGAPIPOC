import sys
import os
from uuid import uuid4

# Add current directory to path
sys.path.append(os.getcwd())

try:
    print("Testing Gemini integration...")
    from app.config import settings
    import google.generativeai as genai
    
    print(f"API Key present: {bool(settings.GEMINI_API_KEY)}")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    print("Listing available models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)

    # model_name = "gemini-1.5-flash-001"
    model_name = "gemini-1.5-flash" # Try the standard one again, maybe listing failed but direct access works if enabled?
    # model_name = "gemini-1.5-flash-001"
    # model_name = "gemini-1.5-flash" 
    # model_name = "gemini-2.0-flash-exp"
    # model_name = "gemini-2.5-flash"
    # model_name = "models/gemini-1.5-flash"
    model_name = "models/gemini-2.5-flash"
    
    print(f"Testing model: {model_name}")
    model = genai.GenerativeModel(model_name)
    try:
        response = model.generate_content("Hello, are you working?")
        print(f"Gemini response: {response.text}")
    except Exception as e:
        print(f"Generate content failed: {e}")
        import traceback
        traceback.print_exc()

    print("\nTesting answer_question function...")
    from app.services.rag_service import answer_question
    from app.models import Message, MessageRole
    
    # Mock history
    history = []
    
    answer, chunks = answer_question(
        user_id=uuid4(),
        notebook_id=uuid4(),
        question="What is the meaning of life?",
        history=history,
        selected_document_ids=[]
    )
    print(f"answer_question result: {answer}")

except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
