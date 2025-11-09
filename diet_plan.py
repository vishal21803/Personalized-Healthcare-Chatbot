import aiohttp
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DietPlanAPI:
    def __init__(self):
        self.api_key = os.getenv("SPOONACULAR_API_KEY")
        self.base_url = "https://api.spoonacular.com/mealplanner/generate"
        logger.debug(f"Initialized DietPlanAPI with api_key: {self.api_key}")

    async def get_diet_plan(self, condition):
        logger.debug(f"Getting diet plan for condition: {condition}")
        if not condition:
            return "No condition provided for diet plan."

        async with aiohttp.ClientSession() as session:
            params = {
                "apiKey": self.api_key,
                "timeFrame": "day",
                "targetCalories": 2000,
                "diet": condition
            }
            logger.debug(f"API request params: {params}")
            async with session.get(self.base_url, params=params) as response:
                logger.debug(f"API response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"API response data: {data}")
                    return self.format_diet_plan(data, condition)
                else:
                    logger.error(f"API request failed with status {response.status}")
                    return f"Failed to fetch diet plan for {condition}. Please try again later."

    def format_diet_plan(self, data, condition):
        diet_plan = f"Diet Plan for {condition}:\n\n"
        meals = data.get('meals', [])
        for meal in meals:
            diet_plan += f"{meal['title']}:\n"
            diet_plan += f"- Ready in: {meal['readyInMinutes']} minutes\n"
            diet_plan += f"- Servings: {meal['servings']}\n"
            diet_plan += f"- Recipe: {meal['sourceUrl']}\n\n"

        nutrients = data.get('nutrients', {})
        diet_plan += f"Total Nutrients:\n"
        diet_plan += f"- Calories: {nutrients.get('calories', 0):.2f}\n"
        diet_plan += f"- Protein: {nutrients.get('protein', 0):.2f}g\n"
        diet_plan += f"- Fat: {nutrients.get('fat', 0):.2f}g\n"
        diet_plan += f"- Carbohydrates: {nutrients.get('carbohydrates', 0):.2f}g\n\n"

        diet_plan += "Note: This is a basic suggestion. Please consult with a nutritionist for a personalized diet plan."
        return diet_plan