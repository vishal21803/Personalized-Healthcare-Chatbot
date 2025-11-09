import aiohttp

class OpenFDAAPI:
    BASE_URL = "https://api.fda.gov/drug/label.json"

    def __init__(self, session):
        self.session = session

    async def get_drug_info(self, drug_name):
        params = {
            "search": f"openfda.brand_name:{drug_name}",
            "limit": 1
        }
        async with self.session.get(self.BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data['results']:
                    result = data['results'][0]
                    return {
                        "brand_name": result['openfda'].get('brand_name', [None])[0],
                        "generic_name": result['openfda'].get('generic_name', [None])[0],
                        "indications_and_usage": result.get('indications_and_usage', [None])[0],
                        "warnings": result.get('warnings', [None])[0],
                        "dosage_and_administration": result.get('dosage_and_administration', [None])[0]
                    }
            return None




