import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class NutritionAPI:
    BASE_URL = "https://trackapi.nutritionix.com/v2"
    
    def __init__(self):
        self.app_id = os.getenv("NUTRITIONIX_APP_ID")
        self.api_key = os.getenv("NUTRITIONIX_API_KEY")
        self.headers = {
            "x-app-id": self.app_id,
            "x-app-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def get_nutrition_info(self, query):
        url = f"{self.BASE_URL}/natural/nutrients"
        data = {"query": query}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None

    def format_nutrition_data(self, data):
        if not data or 'foods' not in data or not data['foods']:
            return "No nutrition information found."

        food = data['foods'][0]  # We'll focus on the first food item
        formatted = f"Nutrition info for {food['food_name']}:\n\n"

        # Main nutrients
        main_nutrients = [
            ('Calories', 'nf_calories', ''),
            ('Total Fat', 'nf_total_fat', 'g'),
            ('Saturated Fat', 'nf_saturated_fat', 'g'),
            ('Cholesterol', 'nf_cholesterol', 'mg'),
            ('Sodium', 'nf_sodium', 'mg'),
            ('Total Carbohydrate', 'nf_total_carbohydrate', 'g'),
            ('Dietary Fiber', 'nf_dietary_fiber', 'g'),
            ('Sugars', 'nf_sugars', 'g'),
            ('Protein', 'nf_protein', 'g')
        ]

        vitamin_keys = {
            'vitamin_a': 'Vitamin A',
            'vitamin_c': 'Vitamin C',
            'vitamin_d': 'Vitamin D',
            'calcium': 'Calcium',
            'iron': 'Iron'
        }

        for key, name in vitamin_keys.items():
            if f'nf_{key}' in food:
                formatted['vitamins'][name] = food[f'nf_{key}']

        for name, key, unit in main_nutrients:
            if key in food:
                formatted += f"{name}: {food[key]}{unit}\n"

        # Vitamins and minerals (top 5)
        vitamins_minerals = [
            ('Vitamin A', 'nf_vitamin_a_dv', '%'),
            ('Vitamin C', 'nf_vitamin_c_dv', '%'),
            ('Calcium', 'nf_calcium_dv', '%'),
            ('Iron', 'nf_iron_dv', '%'),
            ('Potassium', 'nf_potassium', 'mg')
        ]

        formatted += "\nVitamins and Minerals:\n"
        for name, key, unit in vitamins_minerals:
            if key in food:
                formatted += f"{name}: {food[key]}{unit}\n"

        formatted += f"\nServing Size: {food['serving_qty']} {food['serving_unit']}"

        return formatted

nutrition_api = NutritionAPI()