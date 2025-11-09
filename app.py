from flask import jsonify,Flask,request,session,render_template
from flask_cors import CORS
from flask import send_from_directory
import traceback
from chatbot import ChatBot
import speech_recognition as sr
from gtts import gTTS
import os
import uuid
import aiohttp
import asyncio
import time
from api_integration import MedlinePlusAPI
from openfda_api import OpenFDAAPI
from medication_api import MedicationAPI
import xmltodict
import logging
import random
from dotenv import load_dotenv
from nutri import nutrition_api
from diet_plan import DietPlanAPI
from datetime import datetime
import requests
import atexit

load_dotenv()

chat_archives = {}
current_chat = {}

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key_here'  # सत्र के लिए गुप्त कुंजी सेट करें

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



# Define the static folder path
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

patient_history = {}

# Create the static folder if it doesn't exist
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

chatbot = ChatBot()

class ExerciseAPI:
    BASE_URL = "https://wger.de/api/v2"

    async def get_exercises(self, session, category):
        url = f"{self.BASE_URL}/exercise/?language=2&category={category}"
        async with session.get(url) as response:
            data = await response.json()
            return data['results']

    async def search_exercise(self, session, query):
        url = f"{self.BASE_URL}/exercise/search/?term={query}&language=2"
        async with session.get(url) as response:
            data = await response.json()
            return data['suggestions']
        
async def suggest_exercise_routine(self, preferences, health_conditions):
        exercises = {
            "cardio": ["Walking", "Swimming", "Cycling", "Jogging"],
            "strength": ["Push-ups", "Squats", "Lunges", "Planks"],
            "flexibility": ["Yoga", "Stretching", "Pilates"],
            "low_impact": ["Swimming", "Cycling", "Elliptical machine", "Tai Chi"]
        }
        
        routine = []
        
        if "joint issues" in health_conditions:
            routine.extend(random.sample(exercises["low_impact"], 2))
        
        for pref in preferences:
            if pref in exercises:
                routine.extend(random.sample(exercises[pref], 2))
        
        if not routine:
            # If no specific preferences or conditions, get a mix of exercises
            for category in exercises.values():
                routine.extend(random.sample(category, 1))
        
        return list(set(routine)) 

async def get_exercise_info(self, query):
        logger.debug(f"DEBUG: get_exercise_info method called with query: '{query}'")

        try:
            url = f"https://exercisedb.p.rapidapi.com/exercises/name/{query}"
            headers = {
                "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
                "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    exercises = await response.json()
                    logger.debug(f"Exercises data received: {exercises}")

                    if not exercises:
                        return f"Sorry, I couldn't find any information about '{query}'. Please try another exercise."

                    # Get the first (most relevant) result
                    exercise = exercises[0]

                    info = f"Exercise: {exercise['name']}\n\n"
                    info += f"Type: {exercise['type']}\n\n"
                    info += f"Body Part: {exercise['bodyPart']}\n\n"
                    info += f"Equipment: {exercise['equipment']}\n\n"
                    info += f"Target Muscle: {exercise['target']}\n\n"
                    if exercise.get('instructions'):
                        info += "Instructions:\n"
                        for i, step in enumerate(exercise['instructions'], 1):
                            info += f"{i}. {step}\n"

                    logger.debug(f"Formatted exercise info:\n{info}")
                    return info

        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return f"Sorry, an error occurred while fetching information about '{query}'. Please try again later."
async def get_disease_info(disease_name):
    async with aiohttp.ClientSession() as session:
        api = MedlinePlusAPI(session)
        return await api.get_disease_info(disease_name)

async def get_drug_info(drug_name):
    async with aiohttp.ClientSession() as session:
        api = OpenFDAAPI(session)
        return await api.get_drug_info(drug_name)    

async def get_medicines_for_disease(disease_name):
    async with aiohttp.ClientSession() as session:
        api = MedicationAPI(session)
        medicines = await api.get_medicines_for_disease(disease_name)
        logger.debug(f"Medicines returned from API: {medicines}")
        if medicines:
            formatted_info = f"<h2>Medicines for {disease_name}</h2>"
            for medicine in medicines:
                name_to_display = medicine['name'] if medicine['name'] != 'N/A' else medicine['generic_name']
                if name_to_display == 'N/A':
                    name_to_display = "Unknown Medicine"
                
                formatted_info += f"""
                <div class="medicine-info">
                    <h3>{name_to_display}</h3>
                """
                
                if medicine['name'] != 'N/A' and medicine['name'] != medicine['generic_name']:
                    formatted_info += f"<p><strong>Brand Name:</strong> {medicine['name']}</p>"
                
                if medicine['generic_name'] != 'N/A':
                    formatted_info += f"<p><strong>Generic Name:</strong> {medicine['generic_name']}</p>"
                
                if medicine['description'] != 'N/A':
                    formatted_info += f"<h4>Description:</h4><p>{medicine['description']}</p>"
                
                for field in ['indications', 'dosage', 'precautions']:
                    if medicine[field] and medicine[field] != 'N/A':
                        formatted_info += f"""
                        <h4>{field.capitalize()}:</h4>
                        <ul>
                            {format_bullet_points(medicine[field])}
                        </ul>
                        """
                
                formatted_info += "</div><hr>"
            
            logger.debug(f"Formatted info: {formatted_info}")
            return formatted_info
        logger.warning(f"No medicines found for disease: {disease_name}")
        return f"<p>No specific medicine information found for {disease_name}. Please consult with a healthcare professional for accurate medical advice.</p>"

def format_bullet_points(text):
    # Split the text into sentences
    sentences = text.split('. ')
    # Create bullet points, ignoring very short sentences
    return ''.join(f'<li>{sentence}.</li>' for sentence in sentences if len(sentence) > 10)


@app.route('/get_nutrition_info', methods=['POST'])
async def nutrition_info():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    nutrition_data = await nutrition_api.get_nutrition_info(query)
    
    if nutrition_data:
        formatted_data = nutrition_api.format_nutrition_data(nutrition_data)
        return jsonify({
            "message": f"Here's the nutrition information for '{query}':",
            "popupContent": formatted_data,
            "infoType": "nutrition"
        })
    else:
        return jsonify({
            "message": f"Sorry, I couldn't find nutrition information for '{query}'.",
            "infoType": "error"
        })

@app.route('/get_diet_plan', methods=['POST'])
async def get_diet_plan():
    data = request.json
    condition = data.get('condition')
    
    if not condition:
        return jsonify({"error": "No condition provided"}), 400
    
    try:
        diet_plan_api = DietPlanAPI()
        diet_plan = await diet_plan_api.get_diet_plan(condition)
        
        if diet_plan:
            return jsonify({
                "message": diet_plan,
                "infoType": "dietPlan"
            })
        else:
            return jsonify({
                "message": f"Sorry, I couldn't generate a specific diet plan for '{condition}'. Please consult with a nutritionist for personalized advice.",
                "infoType": "error"
            })
    except Exception as e:
        logger.error(f"An error occurred while fetching diet plan: {str(e)}")
        return jsonify({
            "error": f"An error occurred: {str(e)}"
        }), 500

@app.route('/')
def home():
    return render_template('index.html')

# @app.before_app_serving
# async def initialize_chatbot():
#     await chatbot.initialize()

# @app.after_app_serving
# async def shutdown_chatbot():
#     await chatbot.close()


@app.route('/get_response', methods=['POST'])
async def get_response():
    try:
        start_time = time.time()
        await chatbot.initialize()  # Ensure the API session is open
        
        data = request.json
        user_input = data['input']
        symptoms = data.get('symptoms', [])

        is_new_chat = data.get('isNewChat', False)
        is_action_choice = data.get('isActionChoice', False)
        
        if is_new_chat:
            # Reset the chatbot state for new chat
            chatbot.reset()
            return jsonify({
                "message": "How can I assist you today?",
                "showActionButtons": True,
                "state": "initial",
                "options": [
                    {"value": "1", "text": "1. Predict your illness (based on symptoms)"},
                    {"value": "2", "text": "2. Get information about a disease or drug"}
                ]
            })
        
        if is_action_choice:
            # Handle primary choice selection
            chatbot.primary_choice = user_input
            if user_input == "1":
                return jsonify({
                    "message": "Type 1 to start your diagnosis",
                    "state": "gathering_symptoms"
                })
            elif user_input == "2":
                return jsonify({
                    "message": "Please tell me which disease or drug you'd like to know about. Start your message with 'tell me about'.",
                    "state": "awaiting_query"
                })
        
        
        
        print(f"Received input: {user_input}")
        print(f"Symptoms: {symptoms}")
        
        if user_input.lower().startswith("tell me about medicines for"):
            disease_name = user_input[28:].strip()
            print(f"Fetching medicines for disease: {disease_name}")
            medicines_info = await get_medicines_for_disease(disease_name)
            
            if medicines_info:
                info = medicines_info
                info_type = "medicines"
            else:
                info = f"I'm sorry, but I couldn't find any medicine information for {disease_name}."
                info_type = "unknown"
            
            print(f"Fetched medicine info in {time.time() - start_time:.2f} seconds")
            return jsonify({
                "message": f"Here's information about medicines for {disease_name}:",
                "popupContent": info,
                "infoType": info_type
            })
        if user_input.lower().startswith("exercise info"):
            query = user_input[13:].strip()  # Extract the exercise name
            print(f"DEBUG: About to call get_exercise_info with query: '{query}'")
            try:
                exercise_info = await chatbot.get_exercise_info(query)
                print("DEBUG: Exercise info received:")
                print(exercise_info)
            except Exception as e:
                print(f"DEBUG: Error occurred in get_exercise_info: {str(e)}")
                exercise_info = f"An error occurred: {str(e)}"

            print(f"DEBUG: Fetched exercise info in {time.time() - start_time:.2f} seconds")
            return jsonify({
                "message": f"Exercise: {query}\n\n{exercise_info}",
                "infoType": "exercise"
            })

        elif user_input.lower().startswith("fitness routine"):
            target = user_input[15:].strip()
            logger.debug(f"About to call get_fitness_routine with target: '{target}'")
            try:
                fitness_routine = await chatbot.get_fitness_routine(target)
                logger.debug(f"Fitness routine received: {fitness_routine}")
                
                if fitness_routine and isinstance(fitness_routine, dict):
                    response_data = {
                        "message": fitness_routine['routine'],
                        "infoType": "fitnessRoutine",
                        "exercises": fitness_routine.get('exercises', []),
                        "target": fitness_routine.get('target', target)
                    }
                    logger.debug(f"Sending response data: {response_data}")
                    return jsonify(response_data)
                else:
                    logger.warning(f"No fitness routine generated for target: {target}")
                    return jsonify({
                        "message": f"Sorry, I couldn't create a fitness routine for '{target}'. Please try a different target area.",
                        "infoType": "error"
                    })
            except Exception as e:
                logger.error(f"Error occurred in get_fitness_routine: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({
                    "message": f"Sorry, an error occurred while creating a fitness routine for '{target}'. Please try again later.",
                    "infoType": "error"
                })
        elif user_input.lower().startswith("nutrition info"):
            query = user_input[14:].strip()
            print(f"Fetching nutrition info for query: {query}")
            nutrition_info = await chatbot.get_nutrition_info(query)
            
            if nutrition_info:
                return jsonify({
                    "message": nutrition_info,
                    "infoType": "nutrition"
                })
            else:
                return jsonify({
                    "message": f"Sorry, I couldn't find nutrition information for '{query}'.",
                    "infoType": "error"
                })  
        elif user_input.lower().startswith("diet plan for"):
            condition = user_input[14:].strip()
            print(f"Generating diet plan for condition: {condition}")
            diet_plan_api = DietPlanAPI()
            diet_plan = await diet_plan_api.get_diet_plan(condition)
            
            if diet_plan:
                return jsonify({
                    "message": diet_plan,
                    "infoType": "dietPlan"
                })
            else:
                return jsonify({
                    "message": f"Sorry, I couldn't generate a specific diet plan for '{condition}'. Please consult with a nutritionist for personalized advice.",
                    "infoType": "error"
                })     
            
        elif user_input.lower().startswith("tell me about"):
            query = user_input[14:].strip()
            print(f"Fetching info for query: {query}")
            disease_info = await get_disease_info(query)
            drug_info = await get_drug_info(query)
            
            if disease_info:
                info = disease_info
                info_type = "disease"
            elif drug_info:
                info = drug_info
                info_type = "drug"
            else:
                info = f"I'm sorry, but I couldn't find any information about {query}."
                info_type = "unknown"
            
            print(f"Fetched info in {time.time() - start_time:.2f} seconds")
            return jsonify({
                "message": f"Here's information about {query}:",
                "popupContent": info,
                "infoType": info_type
            })
        else:
            response = await chatbot.process_input(user_input, symptoms=symptoms)
        
        if isinstance(response, list):
            # If it's a list of responses, combine them
            combined_response = {
                "message": "\n".join([r.get("message", "") for r in response if r.get("message")]),
                "diagnosis": next((r.get("diagnosis") for r in response if r.get("diagnosis")), None),
                "state": response[-1].get("state"),
                "primaryChoice": response[-1].get("primaryChoice"),
                "symptoms": response[-1].get("symptoms"),
                "diagnosisTime": next((r.get("diagnosisTime") for r in response if r.get("diagnosisTime")), None),
                "showActionButtons": any(r.get("showActionButtons") for r in response),
                "options": next((r.get("options") for r in response if r.get("options")), None),
                "isDiagnosis": any(r.get("diagnosis") for r in response),
            }
            response_data = combined_response
        elif isinstance(response, dict):
            response_data = response
            response_data["isDiagnosis"] = "diagnosis" in response
        else:
            response_data = {
                "message": str(response),
                "symptoms": chatbot.current_symptoms,
                "primaryChoice": chatbot.primary_choice,
                "state": chatbot.state,
                "showActionButtons": chatbot.state == "choose_action",
                "isDiagnosis": False
            }


        if response_data.get("isDiagnosis"):
            print("Setting needs_refresh in session")
            session['needs_refresh'] = True
        
        print(f"Final response data: {response_data}")
        return jsonify(response_data)    
        
        print(f"Is this a diagnosis? {response_data.get('isDiagnosis')}")
        print(f"Total response time: {time.time() - start_time:.2f} seconds")
        return jsonify(response_data)

    except Exception as e:
        print(f"Error in get_response: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/check_refresh', methods=['GET'])
def check_refresh():
    needs_refresh = session.pop('needs_refresh', False)
    print(f"Checking refresh: {needs_refresh}")
    return jsonify({"needs_refresh": needs_refresh})
@app.route('/test_api', methods=['GET'])
async def test_api():
    query = request.args.get('query', 'diabetes')
    
    async with aiohttp.ClientSession() as session:
        disease_info = await get_disease_info(query)
        drug_info = await get_drug_info(query)
    
    return jsonify({
        "query": query, 
        "disease_info": disease_info, 
        "drug_info": drug_info
    })

@app.route('/test_exercise_api', methods=['GET'])
async def test_exercise_api():
    query = request.args.get('query', 'yoga')
    logger.debug(f"Testing exercise API with query: {query}")

    url = f"https://exercisedb.p.rapidapi.com/exercises/name/{query}"
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
    }

    async with aiohttp.ClientSession() as session:
        logger.debug(f"Fetching exercise data from URL: {url}")
        async with session.get(url, headers=headers) as response:
            exercise_data = await response.json()
            logger.debug(f"Exercise data received: {exercise_data}")

    if isinstance(exercise_data, list) and exercise_data:
        # Get the first (most relevant) result
        exercise = exercise_data[0]
        formatted_data = {
            "name": exercise.get('name'),
            "type": exercise.get('type'),
            "bodyPart": exercise.get('bodyPart'),
            "equipment": exercise.get('equipment'),
            "target": exercise.get('target'),
            "instructions": exercise.get('instructions')
        }
    elif isinstance(exercise_data, dict):
        # If it's a dictionary, it might be an error message
        formatted_data = exercise_data
    else:
        formatted_data = "No exercise found or unexpected data format"

    return jsonify({
        "raw_data": exercise_data,
        "formatted_data": formatted_data
    })

@app.route('/test_fitness_routine', methods=['GET'])
async def test_fitness_routine():
    target = request.args.get('target', 'chest')  # Default to 'chest' if no target is provided
    logger.debug(f"Testing fitness routine API with target: {target}")

    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{target}"
            headers = {
                "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
                "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
            }

            async with session.get(url, headers=headers) as response:
                exercises = await response.json()
                logger.debug(f"Received {len(exercises)} exercises for {target}")

                if exercises and isinstance(exercises, list):
                    # Select 5 random exercises
                    selected_exercises = random.sample(exercises, min(5, len(exercises)))
                    
                    routine = f"Fitness routine for {target}:\n\n"
                    for i, exercise in enumerate(selected_exercises, 1):
                        routine += f"{i}. {exercise['name']}\n"
                        routine += f"   Sets: 3, Reps: 12\n"
                        routine += f"   Equipment: {exercise['equipment']}\n\n"
                    
                    routine += "Perform each exercise for 3 sets of 12 repetitions. Rest for 60 seconds between sets."

                    return jsonify({
                        "target": target,
                        "routine": routine,
                        "exercises": [ex['name'] for ex in selected_exercises]
                    })
                else:
                    return jsonify({
                        "error": f"No exercises found for target: {target}"
                    }), 404

        except Exception as e:
            logger.error(f"An error occurred while fetching fitness routine: {str(e)}")
            return jsonify({
                "error": f"An error occurred: {str(e)}"
            }), 500

@app.route('/test_nutrition_api', methods=['GET'])
async def test_nutrition_api():
    query = request.args.get('query', 'banana')  # Default to 'banana' if no query is provided
    logger.debug(f"Testing nutrition API with query: {query}")

    try:
        nutrition_data = await nutrition_api.get_nutrition_info(query)
        logger.debug(f"Nutrition data received: {nutrition_data}")

        if nutrition_data and 'foods' in nutrition_data and nutrition_data['foods']:
            # Get the first (most relevant) result
            food = nutrition_data['foods'][0]
            formatted_data = {
                "food_name": food.get('food_name'),
                "serving_qty": food.get('serving_qty'),
                "serving_unit": food.get('serving_unit'),
                "calories": food.get('nf_calories'),
                "total_fat": food.get('nf_total_fat'),
                "saturated_fat": food.get('nf_saturated_fat'),
                "cholesterol": food.get('nf_cholesterol'),
                "sodium": food.get('nf_sodium'),
                "total_carbohydrate": food.get('nf_total_carbohydrate'),
                "dietary_fiber": food.get('nf_dietary_fiber'),
                "sugars": food.get('nf_sugars'),
                "protein": food.get('nf_protein'),
                "potassium": food.get('nf_potassium'),
                "p": food.get('nf_p')
            }
            
            # Format the nutrition data using the format_nutrition_data method
            formatted_info = nutrition_api.format_nutrition_data(nutrition_data)

            return jsonify({
                "query": query,
                "raw_data": nutrition_data,
                "formatted_data": formatted_data,
                "formatted_info": formatted_info
            })
        else:
            return jsonify({
                "error": f"No nutrition information found for query: {query}"
            }), 404

    except Exception as e:
        logger.error(f"An error occurred while fetching nutrition information: {str(e)}")
        return jsonify({
            "error": f"An error occurred: {str(e)}"
        }), 500   

@app.route('/test_diet_plan_api', methods=['GET'])
async def test_diet_plan_api():
    condition = request.args.get('condition', 'vegetarian')
    logger.debug(f"Testing diet plan API for condition: {condition}")

    try:
        diet_plan_api = DietPlanAPI()
        diet_plan = await diet_plan_api.get_diet_plan(condition)
        
        logger.debug(f"Generated diet plan: {diet_plan}")
        
        return jsonify({
            "condition": condition,
            "diet_plan": diet_plan
        })

    except Exception as e:
        logger.error(f"An error occurred while fetching diet plan: {str(e)}")
        return jsonify({
            "error": f"An error occurred: {str(e)}"
        }), 500

@app.route('/reset_conversation', methods=['POST'])
def reset_conversation():
    try:
        chatbot.reset()

        session.pop('chat_history', None)
        session.pop('current_symptoms', None)
        session.pop('primary_choice', None)
        session.pop('state', None)
        
        
        user_id = session.get('user_id', 'anonymous')
        if user_id in chat_archives:
            chat_archives[user_id].append({'timestamp': datetime.now().isoformat(), 'history': []})
        return jsonify({"message": "Conversation reset successfully"}), 200
    except Exception as e:
        print(f"Error resetting conversation: {e}")
        return jsonify({"error": str(e)}), 500

def save_current_conversation():
    user_id = session.get('user_id', 'anonymous')
    timestamp = datetime.now().isoformat()
    
    if user_id not in chat_archives:
        chat_archives[user_id] = []
    
    chat_archives[user_id].append({
        'timestamp': timestamp,
        'history': session['chat_history']
    })    
@app.route('/start_new_chat', methods=['POST'])
def start_new_chat():
    try:
        user_id = session.get('user_id', 'anonymous')
        print(f"Starting new chat for user: {user_id}")  # Add this line for debugging
        
        # Save current chat to archives if it exists
        if user_id in current_chat and current_chat[user_id]:
            if user_id not in chat_archives:
                chat_archives[user_id] = []
            chat_archives[user_id].append({
                'timestamp': datetime.now().isoformat(),
                'history': current_chat[user_id]
            })
            print(f"Saved current chat to archives. Total chats: {len(chat_archives[user_id])}")  # Add this line for debugging
        
        # Clear current chat
        current_chat[user_id] = []
        
        print("New chat started successfully")  # Add this line for debugging
        return jsonify({"message": "New chat started successfully"}), 200
    except Exception as e:
        print(f"Error starting new chat: {e}")
        return jsonify({"error": str(e)}), 500
@app.route('/auto_save_chat_history', methods=['POST'])
def auto_save_chat_history():
    try:
        data = request.json
        user_id = session.get('user_id', 'anonymous')
        
        if user_id not in current_chat:
            current_chat[user_id] = []
        
        current_chat[user_id] = data['history']
        
        return jsonify({"message": "Chat history auto-saved successfully"}), 200
    except Exception as e:
        print(f"Error auto-saving chat history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/save_chat_history', methods=['POST'])
def save_chat_history():
    try:
        data = request.json
        user_id = session.get('user_id', 'anonymous')
        timestamp = datetime.now().isoformat()
        
        if user_id not in chat_archives:
            chat_archives[user_id] = []
        
        chat_archives[user_id].append({
            'timestamp': timestamp,
            'history': data['history']
        })
        
        return jsonify({"message": "Chat history saved successfully"}), 200
    except Exception as e:
        print(f"Error saving chat history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_archived_chats', methods=['GET'])
def get_archived_chats():
    user_id = session.get('user_id', 'anonymous')
    chats = chat_archives.get(user_id, [])
    return jsonify([{'id': i+1, 'timestamp': chat['timestamp']} for i, chat in enumerate(chats)])

@app.route('/get_archived_chat/<chat_id>', methods=['GET'])
def get_archived_chat(chat_id):
    user_id = session.get('user_id', 'anonymous')
    chats = chat_archives.get(user_id, [])
    try:
        chat_id = int(chat_id)
        if 1 <= chat_id <= len(chats):
            return jsonify(chats[chat_id-1]['history'])
    except ValueError:
        pass
    return jsonify({"error": "Chat not found"}), 404


@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    user_id = session.get('user_id', 'anonymous')
    chats = chat_archives.get(user_id, [])
    return jsonify([{
        'timestamp': chat['timestamp'],
        'messages': chat['history'][:2]  # Only send the first two messages for preview
    } for chat in chats])

@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        
        # Save the audio file temporarily
        temp_filename = f"temp_audio_{uuid.uuid4()}.wav"
        temp_filepath = os.path.join(STATIC_FOLDER, temp_filename)
        audio_file.save(temp_filepath)
        
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(temp_filepath) as source:
            audio = recognizer.record(source)
        
        try:
            text = recognizer.recognize_google(audio, language="en-US")
            print(f"Recognized text: {text}")
            
            # Remove the temporary file
            os.remove(temp_filepath)
            
            return jsonify({"text": text})
        except sr.UnknownValueError:
            return jsonify({"error": "Could not understand audio"}), 400
        except sr.RequestError as e:
            return jsonify({"error": f"Could not request results; {e}"}), 500
    except Exception as e:
        print(f"Error in speech_to_text: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    try:
        data = request.json
        text = data['text']
        tts = gTTS(text=text, lang='en')
        filename = f"speech_{uuid.uuid4()}.mp3"
        file_path = os.path.join(STATIC_FOLDER, filename)
        tts.save(file_path)
        return jsonify({"audio_url": f"/static/{filename}"})
    except Exception as e:
        print(f"Error in text_to_speech: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/user_history', methods=['GET'])
def get_user_history():
    try:
        return jsonify(session.get('chat_history', []))
    except Exception as e:
        print(f"Error getting user history: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    session['chat_history'] = []
    return jsonify({"message": "Chat history cleared successfully"}), 200

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/get_patient_history', methods=['GET'])
def get_patient_history():
    return jsonify(patient_history)

@app.route('/add_patient', methods=['POST'])
def add_patient():
    data = request.json
    patient_name = data['name']
    if patient_name not in patient_history:
        patient_history[patient_name] = {'name': patient_name, 'age': None, 'gender': None, 'symptoms': []}
    return jsonify({"message": "Patient added successfully"})

@app.route('/update_patient', methods=['POST'])
def update_patient():
    data = request.json
    patient_name = data['name']
    if patient_name in patient_history:
        patient_history[patient_name].update(data)
        return jsonify({"message": "Patient updated successfully"})
    return jsonify({"error": "Patient not found"})

@app.route('/clear_patient_history', methods=['POST'])
def clear_patient_history():
    global patient_history
    patient_history = {}
    return jsonify({"message": "Patient history cleared successfully"})

if __name__ == '__main__':
    app.run(debug=True)

if __name__ == '__main__':
    # Initialize chatbot manually
    asyncio.run(chatbot.initialize())
    
    # Run the Flask app
    app.run(debug=True)

atexit.register(lambda: asyncio.run(chatbot.close()))
