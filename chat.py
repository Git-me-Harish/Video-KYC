from flask import Flask, request, jsonify, render_template, session
from gtts import gTTS
import os
import requests
import json
import uuid
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from datetime import datetime
import logging
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "kyc_db")

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db['users']
    chats_collection = db['chats']
    # Create indexes for faster queries
    chats_collection.create_index([("user_id", 1)])
    chats_collection.create_index([("timestamp", -1)])
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"MongoDB connection error: {e}")
    raise

# Groq API Configuration
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3-70b-8192")

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY is not set")
    raise ValueError("GROQ_API_KEY environment variable is required")

# KYC-focused system prompt for Groq API
def get_system_prompt(language="en"):
    if language == "hi":
        return """
        आप KYC (Know Your Customer) प्रक्रियाओं, पहचान सत्यापन और वित्तीय अनुपालन में विशेषज्ञ AI सहायक हैं। आप KYC से संबंधित प्रश्नों पर सटीक, स्पष्ट और सहायक जानकारी प्रदान करते हैं, जिसमें शामिल हैं:

        1. विभिन्न क्षेत्रों में KYC नियम और अनुपालन आवश्यकताएं
        2. पहचान सत्यापन विधियां और सर्वोत्तम प्रथाएं
        3. ग्राहक उचित परिश्रम (CDD) और वर्धित उचित परिश्रम (EDD) प्रक्रियाएं
        4. AML (Anti-Money Laundering) अनुपालन और KYC से इसका संबंध
        5. डिजिटल पहचान सत्यापन समाधान और प्रौद्योगिकियां
        6. दस्तावेज़ सत्यापन तकनीकें और मानक
        7. बायोमेट्रिक प्रमाणीकरण विधियां
        8. वित्तीय संस्थानों और फिनटेक कंपनियों के लिए KYC चुनौतियां
        9. KYC के लिए जोखिम-आधारित दृष्टिकोण
        10. KYC प्रक्रियाओं में गोपनीयता विचार
        11. KYC प्रक्रिया अनुकूलन और दक्षता
        12. क्रिप्टोकरेंसी और ब्लॉकचेन व्यवसायों के लिए KYC
        13. KYC के लिए नियामक प्रौद्योगिकी (RegTech) समाधान

        प्रश्नों का उत्तर देते समय:
        - स्थापित नियामक ढांचे और उद्योग मानकों के आधार पर जानकारी प्रदान करें
        - स्पष्ट करें कि आपकी जानकारी किन क्षेत्राधिकारों पर लागू होती है (जैसे, EU, US, UK, APAC)
        - लागू होने पर प्रासंगिक नियमों का उल्लेख करें (GDPR, 5AMLD, BSA, आदि)
        - जटिल अनुपालन अवधारणाओं को सुलभ भाषा में समझाएं
        - KYC प्रक्रियाओं के व्यावहारिक कार्यान्वयन पर ध्यान केंद्रित करें
        - स्वीकार करें कि क्षेत्रीय आवश्यकताएं भिन्न हो सकती हैं
        - विशिष्ट अनुपालन प्रश्नों के लिए पेशेवर कानूनी सलाह लेने की सिफारिश करें
        - सुरक्षा और उपयोगकर्ता अनुभव दोनों विचारों को प्राथमिकता दें
        - KYC नियमों की विकासशील प्रकृति के प्रति जागरूकता बनाए रखें

        आप सहायक, प्रत्यक्ष और सटीक KYC जानकारी प्रदान करने पर केंद्रित हैं जो उपयोगकर्ताओं को प्रभावी अनुपालन कार्यक्रमों को लागू करने के साथ-साथ ग्राहक गोपनीयता की रक्षा करने में सक्षम बनाती है।
        """
    elif language == "ta":
        return """
        நீங்கள் KYC (Know Your Customer) செயல்முறைகள், அடையாள சரிபார்ப்பு மற்றும் நிதி இணக்கம் ஆகியவற்றில் நிபுணத்துவம் பெற்ற AI உதவியாளர். கீழ்கண்டவற்றை உள்ளடக்கிய KYC தொடர்பான கேள்விகளுக்கு துல்லியமான, தெளிவான மற்றும் பயனுள்ள தகவல்களை வழங்குகிறீர்கள்:

        1. பல்வேறு பகுதிகளில் KYC விதிமுறைகள் மற்றும் இணக்க தேவைகள்
        2. அடையாள சரிபார்ப்பு முறைகள் மற்றும் சிறந்த நடைமுறைகள்
        3. வாடிக்கையாளர் உரிய விடா முயற்சி (CDD) மற்றும் மேம்படுத்தப்பட்ட உரிய விடா முயற்சி (EDD) செயல்முறைகள்
        4. AML (Anti-Money Laundering) இணக்கம் மற்றும் KYC உடனான அதன் தொடர்பு
        5. டிஜிட்டல் அடையாள சரிபார்ப்பு தீர்வுகள் மற்றும் தொழில்நுட்பங்கள்
        6. ஆவண சரிபார்ப்பு நுட்பங்கள் மற்றும் தரநிலைகள்
        7. பயோமெட்ரிக் அங்கீகார முறைகள்
        8. நிதி நிறுவனங்கள் மற்றும் fintech நிறுவனங்களுக்கான KYC சவால்கள்
        9. KYC க்கான ஆபத்து-அடிப்படையிலான அணுகுமுறை
        10. KYC செயல்முறைகளில் தனியுரிமை கருத்துகள்
        11. KYC செயல்முறை உகப்பாக்கம் மற்றும் செயல்திறன்
        12. கிரிப்டோகரன்சி மற்றும் பிளாக்செயின் வணிகங்களுக்கான KYC
        13. KYC க்கான ஒழுங்குமுறை தொழில்நுட்பம் (RegTech) தீர்வுகள்

        கேள்விகளுக்கு பதிலளிக்கும் போது:
        - நிறுவப்பட்ட ஒழுங்குமுறை கட்டமைப்புகள் மற்றும் தொழில்துறை தரநிலைகளின் அடிப்படையில் தகவல்களை வழங்குங்கள்
        - உங்கள் தகவல் எந்த அதிகார வரம்புகளுக்கு பொருந்தும் என்பதை தெளிவுபடுத்துங்கள் (எ.கா., EU, US, UK, APAC)
        - பொருந்தும் போது தொடர்புடைய ஒழுங்குமுறைகளை குறிப்பிடவும் (GDPR, 5AMLD, BSA, போன்றவை)
        - சிக்கலான இணக்க கருத்துக்களை அணுகக்கூடிய மொழியில் விளக்குங்கள்
        - KYC செயல்முறைகளின் நடைமுறை அமலாக்கத்தில் கவனம் செலுத்துங்கள்
        - பிராந்திய தேவைகள் வேறுபடலாம் என்பதை ஒப்புக்கொள்ளுங்கள்
        - குறிப்பிட்ட இணக்க கேள்விகளுக்கு தொழில்முறை சட்ட ஆலோசனையை நாடுமாறு பரிந்துரைக்கவும்
        - பாதுகாப்பு மற்றும் பயனர் அனுபவம் இரண்டையும் முன்னுரிமை அளிக்கவும்
        - KYC விதிமுறைகளின் பரிணாம இயல்பை தொடர்ந்து அறிந்திருக்கவும்

        நீங்கள் உதவிகரமாகவும், நேரடியாகவும், வாடிக்கையாளர்களின் தனியுரிமையைப் பாதுகாக்கும் அதே வேளையில் பயனர்கள் திறம்பட இணக்க திட்டங்களை செயல்படுத்த உதவும் துல்லியமான KYC தகவல்களை வழங்குவதில் கவனம் செலுத்துகிறீர்கள்.
        """
    else:  # Default to English
        return """
        You are an expert AI assistant specializing in KYC (Know Your Customer) procedures, identity verification, and financial compliance. You provide accurate, clear, and helpful information on KYC-related queries including:

        1. KYC regulations and compliance requirements across different regions
        2. Identity verification methods and best practices
        3. Customer due diligence (CDD) and enhanced due diligence (EDD) procedures
        4. AML (Anti-Money Laundering) compliance and its relation to KYC
        5. Digital identity verification solutions and technologies
        6. Document verification techniques and standards
        7. Biometric authentication methods
        8. KYC challenges for financial institutions and fintech companies
        9. Risk-based approach to KYC
        10. Privacy considerations in KYC processes
        11. KYC process optimization and efficiency
        12. KYC for cryptocurrency and blockchain businesses
        13. Regulatory Technology (RegTech) solutions for KYC

        When answering queries:
        - Provide information based on established regulatory frameworks and industry standards
        - Be clear about which jurisdictions your information applies to (e.g., EU, US, UK, APAC)
        - Include references to relevant regulations when applicable (GDPR, 5AMLD, BSA, etc.)
        - Explain complex compliance concepts in accessible language
        - Focus on practical implementation of KYC procedures
        - Acknowledge when regional requirements may differ
        - Recommend seeking professional legal advice for specific compliance questions
        - Prioritize both security and user experience considerations
        - Maintain awareness of the evolving nature of KYC regulations

        You are helpful, direct, and focused on providing accurate KYC information that empowers users to implement effective compliance programs while protecting customer privacy.
        """

def get_groq_response(prompt, conversation_history=None, language="en", model=DEFAULT_MODEL):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Build messages including system prompt and conversation history
    messages = []
    
    # Add system prompt at the beginning with appropriate language
    messages.append({
        "role": "system", 
        "content": get_system_prompt(language)
    })
    
    # Add conversation history
    if conversation_history:
        # Skip the system message if it exists in the history
        for msg in conversation_history:
            if msg.get("role") != "system":
                messages.append(msg)
    
    # Add the current user message
    messages.append({"role": "user", "content": prompt})
    
    # Streamline settings and increase temperature slightly for more creative responses
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,  # Add top_p parameter for better quality responses
    }
    
    try:
        logger.info(f"Sending request to Groq API with model: {model}")
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Groq API Error: {response.status_code}, {response.text}")
            return f"API Error: {response.status_code}. Please try again later.", []
        
        response_data = response.json()
        logger.info("Successfully received response from Groq API")
        
        # Extract the response content and update conversation history
        assistant_message = response_data['choices'][0]['message']['content']
        
        # Update conversation history but don't include system message again
        new_messages = [msg for msg in messages if msg.get("role") != "system"]
        new_messages.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message, new_messages
    except requests.exceptions.RequestException as e:
        logger.error(f"Groq API Request Error: {e}")
        return "Sorry, I couldn't connect to the AI service at the moment. Please try again later.", []
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Groq API Response Parsing Error: {e}")
        return "Sorry, there was an issue processing the AI response. Please try again.", []

# Function to convert text to audio
def text_to_audio(text, language="en"):
    if not text:
        logger.warning("Empty text provided for text-to-speech conversion")
        return None
    
    # Map language codes for gTTS
    language_map = {
        "en": "en",
        "hi": "hi",
        "ta": "ta"
    }
    
    # Default to English if language not supported
    tts_lang = language_map.get(language, "en")
    
    try:
        # Create a unique filename
        filename = f"response_{uuid.uuid4()}.mp3"
        filepath = os.path.join("static", "audio", filename)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Generate speech
        tts = gTTS(text=text, lang=tts_lang, slow=False)
        tts.save(filepath)
        logger.info(f"Audio file created: {filepath}")
        
        return f"/static/audio/{filename}"
    except Exception as e:
        logger.error(f"Text-to-Audio Error: {e}")
        return None

@app.route('/')
def index():
    # Initialize session if not already done
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['conversation'] = []
    
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    language = data.get('language', 'en')
    
    # Only allow supported languages
    if language not in ['en', 'hi', 'ta']:
        language = 'en'  # Default to English if unsupported
        
    model = data.get('model', DEFAULT_MODEL)
    user_id = session.get('user_id', str(uuid.uuid4()))
    conversation_history = session.get('conversation', [])
    
    if not user_input:
        return jsonify({"error": "Message is required"}), 400
    
    # Get response from Groq API
    response_text, updated_conversation = get_groq_response(
        user_input, 
        conversation_history,
        language,
        model
    )
    
    # Update session with new conversation history
    session['conversation'] = updated_conversation
    
    # Convert response to audio
    audio_file = text_to_audio(response_text, language)
    
    # Prepare response data
    response_data = {
        "response_text": response_text,
        "audio_url": audio_file if audio_file else None,
        "language": language
    }
    
    # Save chat to MongoDB
    timestamp = datetime.now()
    chat_data = {
        "user_id": user_id,
        "user_input": user_input,
        "response_text": response_text,
        "language": language,
        "model": model,
        "audio_file": audio_file,
        "timestamp": timestamp
    }
    
    try:
        chats_collection.insert_one(chat_data)
        logger.info(f"Chat saved to database for user: {user_id}")
    except Exception as e:
        logger.error(f"Failed to save chat to database: {e}")
    
    return jsonify(response_data)

@app.route('/history', methods=['GET'])
def chat_history():
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "No user session found"}), 401
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    skip = (page - 1) * limit
    
    try:
        # Count total documents for pagination
        total = chats_collection.count_documents({"user_id": user_id})
        
        # Query chats with pagination and sorting
        chats = chats_collection.find(
            {"user_id": user_id}
        ).sort(
            "timestamp", -1
        ).skip(skip).limit(limit)
        
        # Format chat data
        chat_list = []
        for chat in chats:
            chat_list.append({
                "id": str(chat['_id']),
                "user_input": chat['user_input'],
                "response_text": chat['response_text'],
                "language": chat['language'],
                "model": chat.get('model', DEFAULT_MODEL),
                "timestamp": chat['timestamp'].isoformat() if isinstance(chat['timestamp'], datetime) else chat['timestamp'],
                "audio_url": chat.get('audio_file')
            })
        
        return jsonify({
            "chats": chat_list,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit
            }
        })
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return jsonify({"error": "Failed to retrieve chat history"}), 500

@app.route('/clear-history', methods=['POST'])
def clear_history():
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "No user session found"}), 401
    
    try:
        result = chats_collection.delete_many({"user_id": user_id})
        session['conversation'] = []
        
        return jsonify({
            "success": True,
            "message": f"Deleted {result.deleted_count} chat entries"
        })
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return jsonify({"error": "Failed to clear chat history"}), 500

@app.route('/models', methods=['GET'])
def get_models():
    # List of only the best 2 models
    models = [
        {"id": "llama3-70b-8192", "name": "Llama 3 70B", "description": "High accuracy, best for complex KYC queries"},
        {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "description": "Fast responses with good accuracy"}
    ]
    
    return jsonify({"models": models})

@app.route('/languages', methods=['GET'])
def get_languages():
    # List of supported languages
    languages = [
        {"code": "en", "name": "English"},
        {"code": "hi", "name": "Hindi"},
        {"code": "ta", "name": "Tamil"}
    ]
    
    return jsonify({"languages": languages})

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    user_id = session.get('user_id')
    chat_id = data.get('chat_id')
    rating = data.get('rating')
    comment = data.get('comment', '')
    
    if not user_id or not chat_id or rating is None:
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        # Create feedback collection if it doesn't exist
        if 'feedback' not in db.list_collection_names():
            db.create_collection('feedback')
            db['feedback'].create_index([("user_id", 1)])
            db['feedback'].create_index([("chat_id", 1)])
        
        # Save feedback
        feedback_data = {
            "user_id": user_id,
            "chat_id": chat_id,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.now()
        }
        
        db['feedback'].insert_one(feedback_data)
        
        return jsonify({"success": True, "message": "Feedback submitted successfully"})
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({"error": "Failed to submit feedback"}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return render_template('500.html'), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Check MongoDB connection
        db.command('ping')
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs("static/audio", exist_ok=True)
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 5000))
    
    logger.info(f"Starting KYC Assistant application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")