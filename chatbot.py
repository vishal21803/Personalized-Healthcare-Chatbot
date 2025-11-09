import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
import csv
from datetime import datetime
import json
import os
from api_integration import MedlinePlusAPI
import aiohttp
import re
from html import escape, unescape
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from collections import Counter
from bs4 import BeautifulSoup
import webbrowser
from openfda_api import OpenFDAAPI
from medication_api import MedicationAPI
import time
import random
import logging
from nutri import nutrition_api


logger = logging.getLogger(__name__)


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


class ChatBot:
    def __init__(self):
        self.symptom = ""
        self.days = 0
        self.additional_symptoms = []
        self.state = "ask_name"
        self.conversation_history = []
        self.current_patient = None
        self.current_symptoms = []
        self.diagnosis = None
        self.diagnosis_time = None  # Add this line
        self.history_file = 'conversation_history.json'
        self.load_data()
        self.load_history()
        self.history = []
        self.api_session = None
        self.state="initial"
        self.primary_choice = None
        self.exercise_api = ExerciseAPI()
        



    def load_data(self):
        try:
            self.training = pd.read_csv('Data/Training.csv')
            self.testing = pd.read_csv('Data/Testing.csv')
            self.x = self.training.iloc[:, :-1]
            self.y = self.training.iloc[:, -1]
            self.x_train, self.x_test, self.y_train, self.y_test = train_test_split(self.x, self.y, test_size=0.3, random_state=20)
            self.clf = DecisionTreeClassifier()
            self.clf.fit(self.x_train, self.y_train)
            self.load_symptom_data()
            print(f"Shape of self.x: {self.x.shape}")
            print(f"Columns in self.x: {self.x.columns}")
        except Exception as e:
            print(f"Error loading data: {e}")
            raise

    def load_symptom_data(self):
        self.severity_dict = {}
        self.description_dict = {}
        self.precaution_dict = {}

        try:
            with open('MasterData/symptom_severity.csv', encoding='utf-8') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                next(csv_reader)  # Skip header
                for row in csv_reader:
                    if len(row) >= 2:
                        self.severity_dict[row[0]] = int(row[1])

            with open('MasterData/symptom_description.csv', encoding='utf-8') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                next(csv_reader)  # Skip header
                for row in csv_reader:
                    if len(row) >= 2:
                        self.description_dict[row[0]] = row[1]

            with open('MasterData/symptom_precaution.csv', encoding='utf-8') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                next(csv_reader)  # Skip header
                for row in csv_reader:
                    if len(row) >= 5:
                        self.precaution_dict[row[0]] = [row[1], row[2], row[3], row[4]]
        except Exception as e:
            print(f"Error loading symptom data: {e}")
            raise

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.conversation_history = json.load(f)
                print("Loaded history:", self.conversation_history)  # Debug log
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in history file: {e}")
                print("Initializing empty history due to corrupt file.")
                self.conversation_history = {}
                # Optionally, you can rename the corrupt file for later inspection
                os.rename(self.history_file, f"{self.history_file}.corrupt")
        else:
            self.conversation_history = {}
            print("No history file found, initialized empty history")  # Debug log

    def save_history(self):
        print("Saving history:", self.conversation_history)  # Debug log
        with open(self.history_file, 'w') as f:
            json.dump(self.conversation_history, f)

    
    async def initialize(self):
        if not self.api_session or self.api_session.closed:
            self.api_session = aiohttp.ClientSession()

    async def close(self):
        if self.api_session and not self.api_session.closed:

            await self.api_session.close()   


    def create_html_page(self, content):
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Health Information Chatbot</title>
            <style>
                 body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f0f2f5;
            margin: 0;
            padding: 20px;
        }}
        .chat-container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .chat-header {{
            background-color: #075e54;
            color: white;
            padding: 20px;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
        }}
        .chat-body {{
            padding: 20px;
        }}
        .message {{
            background-color: #FFF3E0;  /* हल्का नारंगी पृष्ठभूमि */
            padding: 15px 20px;
            border-radius: 18px;
            margin-bottom: 20px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            line-height: 1.6;
        }}

        .message-content h2 {{
    color: #4682b4;
    margin-top: 0;
}}

.message-content ul {{
    padding-left: 20px;
}}

.message-content li {{
    margin-bottom: 5px;
}}
        .message h2 {{
            color: #075e54;
            margin-top: 0;
        }}
                ul {{
                    padding-left: 20px;
                    margin-bottom: 15px;
                }}
                li {{
                    margin-bottom: 8px;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 15px;
                    border-radius: 8px;
                    border: 1px solid #ddd;
                    white-space: pre-wrap;
                    font-size: 14px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="chat-container">
                <div class="chat-header">
                    Health Information Chatbot
                </div>
                <div class="chat-body">
                    <div class="message">
                        <div id="original-html">{}</div>
                    </div>
                </div>
            </div>

            <script>
                // Function to convert HTML into structured text format
                function convertHTMLToStructuredFormat(htmlElement) {{
                    let structuredText = '';
                    
                    function extractText(node) {{
                        if (node.nodeType === Node.TEXT_NODE) {{
                            return node.textContent.trim();
                        }}
                        if (node.nodeType === Node.ELEMENT_NODE) {{
                            let tagName = node.tagName.toLowerCase();
                            let text = '';

                            if (tagName === 'h1' || tagName === 'h2' || tagName === 'h3') {{
                                text += '\\n' + node.textContent.trim().toUpperCase() + '\\n';
                            }} else if (tagName === 'ul') {{
                                text += '\\n';
                                node.querySelectorAll('li').forEach(li => {{
                                    text += ' - ' + li.textContent.trim() + '\\n';
                                }});
                            }} else {{
                                text += node.textContent.trim();
                            }}

                            return text;
                        }}
                        return '';
                    }}

                    htmlElement.childNodes.forEach(node => {{
                        structuredText += extractText(node) + '\\n';
                    }});

                    return structuredText.trim();
                }}

                // Get the HTML content and convert it
                const originalHtml = document.getElementById('original-html').innerHTML;
                const structuredOutput = convertHTMLToStructuredFormat(document.getElementById('original-html'));
                document.getElementById('structured-output').textContent = structuredOutput;
            </script>
        </body>
        </html>
        """
        
        formatted_html = html_content.format(content)
        
        # Save the HTML content to a file
        with open('disease_info.html', 'w', encoding='utf-8') as f:
            f.write(formatted_html)
        
        # Open the HTML file in the default web browser
        webbrowser.open('disease_info.html')    


    
    async def get_formatted_disease_info(self, disease_name):
            start_time = time.time()
            if not self.api_session:
                await self.initialize()
            
            api = MedlinePlusAPI(self.api_session)
            try:
                print(f"Fetching info for {disease_name} from MedlinePlus API")
                info = await api.get_disease_info(disease_name)
                print(f"Received info from API in {time.time() - start_time:.2f} seconds")

                if info.startswith("Error"):
                    return f"<p>{info}</p>"
                elif info.startswith("Unable to fetch"):
                    return f"<p>{info}</p>"
                else:
                    # Parse the information
                    title, summary = info.split("\n", 1)
                    title = title.replace("Title: ", "")
                    summary = summary.replace("Summary: ", "")

                    # Format the information as HTML
                    formatted_info = f"""
                        <h2>{title}</h2>
                        <div>{summary}</div>
                    """
                    print(f"Formatted info in {time.time() - start_time:.2f} seconds")
                    return formatted_info
            except Exception as e:
                print(f"Error in get_formatted_disease_info: {e}")
                return f"<p>An error occurred while fetching information: {str(e)}</p>"
            

    async def get_formatted_drug_info(self, drug_name):
            start_time = time.time()
            if not self.api_session:
                await self.initialize()
            
            api = OpenFDAAPI(self.api_session)
            try:
                print(f"Fetching info for {drug_name} from OpenFDA API")
                info = await api.get_drug_info(drug_name)
                print(f"Received info from API in {time.time() - start_time:.2f} seconds")

                if info is None:
                    return f"I'm sorry, but I couldn't find any information about {drug_name} in the OpenFDA database."

                formatted_info = f"Here's information about {drug_name}:\n\n"
                formatted_info += f"Description: {info['description']}\n\n"
                formatted_info += f"Indications and Usage: {info['indications_and_usage']}\n\n"
                formatted_info += f"Warnings: {info['warnings']}\n\n"
                formatted_info += f"Dosage and Administration: {info['dosage_and_administration']}"

                return self.create_html_content(formatted_info)
            except Exception as e:
                print(f"Error fetching drug info: {e}")
                return f"I'm sorry, but I encountered an error while fetching information about {drug_name}. Please try again later."

    async def get_medicines_for_disease(self, disease_name):
        try:
            medicines = await self.medication_api.get_medicines_for_disease(disease_name)
            if not medicines:
                return f"I'm sorry, but I couldn't find any specific medicine information for {disease_name}."

            formatted_info = f"<h3>Medicines related to {disease_name}:</h3>"
            for medicine in medicines:
                formatted_info += f"""
                <div class="medicine-info">
                    <h4>{medicine['name']} ({medicine['generic_name']})</h4>
                    <p><strong>Description:</strong> {medicine['description']}</p>
                    <p><strong>Indications:</strong> {medicine['indications']}</p>
                    <p><strong>Dosage:</strong> {medicine['dosage']}</p>
                    <p><strong>Precautions:</strong> {medicine['precautions']}</p>
                </div>
                """
            return formatted_info
        except Exception as e:
            print(f"Error fetching medicine info: {e}")
            return f"I'm sorry, but I encountered an error while fetching information about medicines for {disease_name}. Please try again later."   
  
    async def get_exercise_info(self, query):
            logger.debug(f"Starting get_exercise_info for query: '{query}'")
            if not self.api_session:
                await self.initialize()

            try:
                url = f"https://exercisedb.p.rapidapi.com/exercises/name/{query}"
                headers = {
                    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
                    "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
                }

                async with self.api_session.get(url, headers=headers) as response:
                    exercises = await response.json()
                    logger.debug(f"Exercises data received: {exercises}")

                    if exercises and isinstance(exercises, list):
                        exercise = exercises[0]  # Get the first (most relevant) result
                        info = f"Exercise: {exercise.get('name', 'N/A')}\n\n"
                        info += f"Type: {exercise.get('type', 'N/A')}\n\n"
                        info += f"Body Part: {exercise.get('bodyPart', 'N/A')}\n\n"
                        info += f"Equipment: {exercise.get('equipment', 'N/A')}\n\n"
                        info += f"Target Muscle: {exercise.get('target', 'N/A')}\n\n"
                        
                        if exercise.get('instructions'):
                            info += "Instructions:\n"
                            for i, step in enumerate(exercise['instructions'], 1):
                                info += f"{i}. {step}\n"

                        logger.debug(f"Formatted exercise info:\n{info}")
                        return info
                    else:
                        return f"Sorry, I couldn't find any information about '{query}'. Please try another exercise or fitness-related term."

            except Exception as e:
                logger.error(f"An error occurred while fetching exercise info: {str(e)}")
                return f"Sorry, an error occurred while fetching information about '{query}'. Please try again later."

    async def get_fitness_routine(self, target):
        logger.debug(f"Getting fitness routine for target: {target}")
        url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{target}"
        headers = {
            "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
            "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                exercises = await response.json()
                logger.debug(f"Received {len(exercises)} exercises from API")

                if exercises and isinstance(exercises, list):
                    selected_exercises = random.sample(exercises, min(5, len(exercises)))
                    
                    routine = f"Fitness routine for {target}:\n\n"
                    exercise_names = []
                    for i, exercise in enumerate(selected_exercises, 1):
                        exercise_name = exercise['name']
                        exercise_names.append(exercise_name)
                        routine += f"{i}. {exercise_name}\n"
                        routine += f"   Sets: 3, Reps: 12\n"
                        routine += f"   Equipment: {exercise['equipment']}\n\n"
                    
                    routine += "Perform each exercise for 3 sets of 12 repetitions. Rest for 60 seconds between sets."
                    
                    result = {
                        "routine": routine,
                        "exercises": exercise_names,
                        "target": target
                    }
                    logger.debug(f"Generated fitness routine: {result}")
                    return result
                else:
                    logger.warning(f"No exercises found for target: {target}")
                    return None   
    async def get_nutrition_info(self, query):
        nutrition_data = await nutrition_api.get_nutrition_info(query)
        if nutrition_data:
            return nutrition_api.format_nutrition_data(nutrition_data)
        return None
    
    async def get_diet_plan(self, condition):
        try:
            diet_plan = await self.diet_plan_api.get_diet_plan(condition)
            if diet_plan:
                return diet_plan
            else:
                return f"Sorry, I couldn't generate a specific diet plan for '{condition}'. Please consult with a nutritionist for personalized advice."
        except Exception as e:
            print(f"Error in get_diet_plan: {e}")
            return f"An error occurred while fetching the diet plan for '{condition}'. Please try again later."

      
        
    def create_html_content(self, content):
            html_content = """
            <div class="disease-info">
                <div class="message">
                    {}
                </div>
            </div>
            """
            return html_content.format(content)            

   
    async def process_input(self, user_input, patient_name=None, patient_age=None, patient_gender=None, symptoms=None):
        response = "I'm sorry, I didn't understand that. Let's start over."

        if symptoms:
            self.current_symptoms.extend(symptoms)

        if user_input.lower().startswith("tell me about exercise"):
            query = user_input[22:].strip()
            exercise_info = await self.get_exercise_info(query)
            return {
                "message": f"Here's information about the exercise '{query}':",
                "popupContent": exercise_info,
                "infoType": "exercise"
            }
        elif user_input.lower().startswith("fitness routine"):
            target = user_input[15:].strip()
            if not target:
                return {
                    "message": "Please specify a target body part for your fitness routine. For example: 'fitness routine chest' or 'fitness routine legs'.",
                    "infoType": "help"
                }
            routine = await self.get_fitness_routine(target)
            return {
                "message": routine,
                "infoType": "fitnessRoutine"
            }   
        elif user_input.lower().startswith("nutrition info"):
            query = user_input[14:].strip()
            nutrition_info = await self.get_nutrition_info(query)
            if nutrition_info:
                return {
                    "message": nutrition_info,
                    "infoType": "nutrition"
                }
            else:
                return {
                    "message": f"Sorry, I couldn't find nutrition information for '{query}'.",
                    "infoType": "error"
                } 
        elif user_input.lower().startswith("diet plan for"):
            condition = user_input[14:].strip()
            diet_plan = await self.get_diet_plan(condition)
            return {
                "message": diet_plan,
                "infoType": "dietPlan"
            }          
        elif user_input.lower().startswith("tell me about medicines for"):
            disease_name = user_input[28:].strip()
            medicines_info = await self.get_medicines_for_disease(disease_name)
            return {
                "message": f"Here's information about medicines for {disease_name}:",
                "popupContent": medicines_info,
                "state": self.state
            }    

        if self.state == "initial" or self.state == "choose_action":
            self.state = "choose_action"
            if user_input.lower() in ["1", "predict", "illness", "symptoms"]:
                self.state = "ask_symptom"
                self.primary_choice = 1
                return "What symptom are you experiencing?"
            elif user_input.lower() in ["2", "information", "disease", "drug"]:
                self.state = "ask_info"
                self.primary_choice = 2
                return "What disease or drug would you like information about? (Please type: Tell me about [disease/drug name])"
            else:
                return {
                    "message": "How can I assist you today?",
                    "showActionButtons": True,
                    "options": [
                        {"text": "1. Predict your illness (based on symptoms)", "value": "1"},
                        {"text": "2. Get information about a disease or drug", "value": "2"}
                    ]
                }
        elif self.state == "ask_symptom":
            self.symptom = user_input.lower().strip()
            if self.symptom in self.x.columns:
                self.current_symptoms.append(self.symptom)
                self.state = "ask_days"
                response = f"For how many days have you been feeling {self.symptom}?"
            else:
                response = f"I'm sorry, but I don't have information about the symptom '{self.symptom}'. Please try another symptom."
        elif self.state == "ask_days":
            try:
                days = int(user_input)
                if days > 0:
                    self.days = days
                    self.state = "ask_additional"
                    self.related_symptoms = self.get_related_symptoms()
                    if self.related_symptoms:
                        response = f"Are you also experiencing {self.related_symptoms[0]}? (Yes/No)"
                    else:
                        return self.conclude_diagnosis()
                else:
                    response = "Please enter a positive number of days."
            except ValueError:
                response = "Please enter a valid number of days."

        elif self.state == "ask_additional":
            user_input = user_input.lower().strip()
            if user_input in ['yes', 'no']:
                if user_input == 'yes':
                    self.current_symptoms.append(self.related_symptoms[0])
                self.related_symptoms = self.related_symptoms[1:]
                
                if self.related_symptoms:
                    response = f"Are you also experiencing {self.related_symptoms[0]}? (Yes/No)"
                else:
                    diagnosis_result = self.conclude_diagnosis()
                    action_buttons = {
                        "message": "What would you like to do next?",
                        "showActionButtons": True,
                        "options": [
                            {"text": "1. Predict your illness (based on symptoms)", "value": "1"},
                            {"text": "2. Get information about a disease or drug", "value": "2"}
                        ]
                    }
                    return [diagnosis_result, action_buttons]  # Return both responses
            else:
                response = "Please answer with 'Yes' or 'No'."         
        
        elif self.state == "ask_info":
            if user_input.lower().startswith("tell me about"):
                query = user_input[14:].strip()
                disease_info = await self.get_formatted_disease_info(query)
                drug_info = await self.get_formatted_drug_info(query)
                if disease_info.startswith("Here's information about"):
                    response = disease_info
                elif drug_info.startswith("Here's information about"):
                    response = drug_info
                else:
                    response = f"I'm sorry, but I couldn't find any information about {query}."
                return self.conclude_info(response)
            else:
                response = "Please start your query with 'Tell me about'"

        # Save conversation history
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if current_time not in self.conversation_history:
            self.conversation_history[current_time] = []
        
        self.conversation_history[current_time].append({
            "patient": self.current_patient,
            "symptoms": self.current_symptoms.copy(),
            "diagnosis": self.diagnosis,
            "diagnosis_time": self.diagnosis_time,
            "conversation": (user_input, response)
        })
        
        await self.save_history()
        
        return {
        "message": response,
        "state": self.state,
        "primaryChoice": self.primary_choice,
        "symptoms": self.current_symptoms,
        "diagnosis": self.diagnosis,
        "diagnosisTime": self.diagnosis_time,
        "showActionButtons": self.state == "choose_action",
        "diagnosisComplete": self.state == "choose_action",  # Add this flag

        "options": [
            {"text": "1. Predict your illness (based on symptoms)", "value": "1"},
            {"text": "2. Get information about a disease or drug", "value": "2"}
        ] if self.state == "choose_action" else None
    }

    def get_conversation_history(self):
        return self.conversation_history

    def conclude_diagnosis(self):
        self.diagnosis = self.get_conclusion()
        self.diagnosis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.state = "choose_action"
        self.primary_choice = None
        return {
            "message": f"{self.diagnosis}\n\n",
            "state": self.state,
            "primaryChoice": self.primary_choice,
            "symptoms": self.current_symptoms,
            "diagnosis": self.diagnosis,
            "diagnosisTime": self.diagnosis_time,

            "diagnosisComplete": True

            
        }

    def conclude_info(self, info_response):
        self.state = "choose_action"
        self.primary_choice = None
        return {
            "message": f"{info_response}\n\nWhat would you like to do next?",
            "state": self.state,
            "primaryChoice": self.primary_choice,
            "showActionButtons": True,
            "options": [
                {"text": "1. Predict your illness (based on symptoms)", "value": "1"},
                {"text": "2. Get information about a disease or drug", "value": "2"}
            ]
        }
        
    async def save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.conversation_history, f)
    def get_related_symptoms(self):
        try:
            if self.symptom not in self.x.columns:
                print(f"Symptom '{self.symptom}' not found in the dataset.")
                return []
            
            symptom_rows = self.x[self.x[self.symptom] == 1]
            
            if symptom_rows.empty:
                print(f"No data found for symptom '{self.symptom}'.")
                return []
            
            related_symptoms = symptom_rows.sum().sort_values(ascending=False)
            related_symptoms = related_symptoms[related_symptoms.index != self.symptom]
            top_5_related = related_symptoms.nlargest(10).index.tolist()
            
            return top_5_related
        except Exception as e:
            print(f"Error in get_related_symptoms: {e}")
            return []

    def get_conclusion(self):
        try:
            input_vector = np.zeros(len(self.x.columns))
            for sym in self.current_symptoms:
                if sym in self.x.columns:
                    input_vector[self.x.columns.get_loc(sym)] = 1

            prediction = self.clf.predict([input_vector])[0]
            
            severity = self.calculate_severity()
            description = self.description_dict.get(prediction, "No description available.")
            precautions = self.precaution_dict.get(prediction, ["No specific precautions available."])
            
            advice = f"Based on your symptoms, you may have {prediction}.\n"
            advice += f"Description: {description}\n"
            advice += f"The condition appears to be {severity}.\n"
            advice += "Precautions:\n"
            for i, precaution in enumerate(precautions, 1):
                advice += f"{i}. {precaution}\n"
            advice += "Please consult a doctor for proper diagnosis and treatment."
            
            return advice
        except Exception as e:
            print(f"Error in get_conclusion: {e}")
            return "I'm sorry, but I couldn't generate a conclusion based on the provided symptoms. Please consult a doctor for proper diagnosis."

    def calculate_severity(self):
        severity_score = sum(self.severity_dict.get(sym, 0) for sym in self.current_symptoms)
        if severity_score <= 3:
            return "mild"
        elif severity_score <= 6:
            return "moderate"
        else:
            return "severe"

    def get_user_history(self):
        print("Returning history:", self.conversation_history)  # Debug log
        formatted_history = {}
        for time, entries in self.conversation_history.items():
            for entry in entries:
                patient = entry['patient']
                if patient not in formatted_history:
                    formatted_history[patient] = []
                formatted_history[patient].append({
                    "symptoms": entry['symptoms'],
                    "diagnosis": entry['diagnosis'],
                    "diagnosis_time": entry['diagnosis_time'],
                    "conversation_time": time
                })
        return formatted_history

    def is_diagnosis_complete(self, patient_name):
        return self.state == "conclude" and self.current_patient == patient_name

    def get_diagnosis(self, patient_name):
        if self.is_diagnosis_complete(patient_name):
            return {
                "diagnosis": self.diagnosis,
                "symptoms": self.current_symptoms,
                "diagnosis_time": self.diagnosis_time
            }
        return None

    def reset(self):
        
        self.symptom = ""
        self.days = 0
        self.additional_symptoms = []
        self.state = "ask_name"
        self.current_patient = None
        self.current_symptoms = []
        self.diagnosis = None
        self.diagnosis_time = None  # Add this line
        self.state = "initial"
        self.primary_choice = None
        self.conversation_history=[]
        self.__init__()