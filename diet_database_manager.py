import json
import os

class DietDatabaseManager:
    def __init__(self, filename='diet_recommendations.json'):
        self.filename = filename
        self.database = self.load_database()

    def load_database(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as file:
                return json.load(file)
        return {}

    def save_database(self):
        with open(self.filename, 'w') as file:
            json.dump(self.database, file, indent=2)

    def add_disease(self, disease_name):
        if disease_name not in self.database:
            self.database[disease_name] = {
                "overview": "",
                "foods_to_eat": [],
                "foods_to_avoid": [],
                "meal_plan": [],
                "tips": []
            }
            print(f"Added {disease_name} to the database.")
        else:
            print(f"{disease_name} already exists in the database.")

    def update_disease_info(self, disease_name, key, value):
        if disease_name in self.database:
            self.database[disease_name][key] = value
            print(f"Updated {key} for {disease_name}.")
        else:
            print(f"{disease_name} not found in the database.")

    def view_disease(self, disease_name):
        if disease_name in self.database:
            print(f"\nDiet Recommendations for {disease_name}:")
            for key, value in self.database[disease_name].items():
                print(f"\n{key.capitalize()}:")
                if isinstance(value, list):
                    for item in value:
                        print(f"- {item}")
                else:
                    print(value)
        else:
            print(f"{disease_name} not found in the database.")

    def list_diseases(self):
        print("\nDiseases in the database:")
        for disease in self.database.keys():
            print(f"- {disease}")

def main():
    manager = DietDatabaseManager()

    while True:
        print("\n1. Add a new disease")
        print("2. Update disease information")
        print("3. View disease recommendations")
        print("4. List all diseases")
        print("5. Save and exit")

        choice = input("Enter your choice (1-5): ")

        if choice == '1':
            disease_name = input("Enter the disease name: ").lower()
            manager.add_disease(disease_name)

        elif choice == '2':
            disease_name = input("Enter the disease name: ").lower()
            if disease_name in manager.database:
                print("Select the information to update:")
                print("1. Overview")
                print("2. Foods to eat")
                print("3. Foods to avoid")
                print("4. Meal plan")
                print("5. Tips")
                update_choice = input("Enter your choice (1-5): ")
                
                if update_choice in ['1', '2', '3', '4', '5']:
                    keys = ['overview', 'foods_to_eat', 'foods_to_avoid', 'meal_plan', 'tips']
                    key = keys[int(update_choice) - 1]
                    if key == 'overview':
                        value = input("Enter the new overview: ")
                    else:
                        value = input(f"Enter {key} (comma-separated): ").split(',')
                    manager.update_disease_info(disease_name, key, value)
                else:
                    print("Invalid choice.")
            else:
                print(f"{disease_name} not found in the database.")

        elif choice == '3':
            disease_name = input("Enter the disease name: ").lower()
            manager.view_disease(disease_name)

        elif choice == '4':
            manager.list_diseases()

        elif choice == '5':
            manager.save_database()
            print("Database saved. Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()