import aiohttp
import urllib.parse
import xmltodict
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MedicationAPI:
    def __init__(self, session):
        self.session = session
        self.openfda_url = "https://api.fda.gov/drug/label.json"
        self.rxnorm_url = "https://rxnav.nlm.nih.gov/REST"
        self.dailymed_url = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

   
    async def get_medicines_for_disease(self, disease_name):
        encoded_disease = urllib.parse.quote(disease_name)
        url = f"{self.openfda_url}?search=indications_and_usage:{encoded_disease}&limit=10"
        
        logger.debug(f"Fetching medicines for disease: {disease_name}")
        logger.debug(f"URL: {url}")

        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                logger.debug(f"OpenFDA API response: {data}")
                if 'results' in data:
                    medicines = []
                    for result in data['results']:
                        medicine = {
                            'name': 'N/A',
                            'generic_name': 'N/A',
                            'description': result.get('description', ['N/A'])[0],
                            'indications': result.get('indications_and_usage', ['N/A'])[0],
                            'dosage': result.get('dosage_and_administration', ['Consult with your doctor'])[0],
                            'precautions': result.get('precautions', ['Consult with your doctor for specific precautions'])[0]
                        }

                        # Try to get name from OpenFDA
                        if 'openfda' in result:
                            medicine['name'] = result['openfda'].get('brand_name', ['N/A'])[0]
                            medicine['generic_name'] = result['openfda'].get('generic_name', ['N/A'])[0]

                        logger.debug(f"Initial medicine info: {medicine}")

                        # If name is still N/A, try RxNorm
                        if medicine['name'] == 'N/A' or medicine['generic_name'] == 'N/A':
                            rxnorm_info = await self.get_rxnorm_info(medicine['generic_name'] if medicine['generic_name'] != 'N/A' else medicine['name'])
                            if rxnorm_info:
                                if medicine['name'] == 'N/A':
                                    medicine['name'] = rxnorm_info.get('name', 'N/A')
                                if medicine['generic_name'] == 'N/A':
                                    medicine['generic_name'] = rxnorm_info.get('generic_name', 'N/A')

                        # If name is still N/A, try DailyMed
                        if medicine['name'] == 'N/A' or medicine['generic_name'] == 'N/A':
                            dailymed_info = await self.get_dailymed_info(result['id'])
                            if dailymed_info:
                                if medicine['name'] == 'N/A':
                                    medicine['name'] = dailymed_info.get('name', 'N/A')
                                if medicine['generic_name'] == 'N/A':
                                    medicine['generic_name'] = dailymed_info.get('generic_name', 'N/A')

                        # Include the medicine if it has a name, generic name, or description
                        if medicine['name'] != 'N/A' or medicine['generic_name'] != 'N/A' or medicine['description'] != 'N/A':
                            logger.debug(f"Final medicine info: {medicine}")
                            medicines.append(medicine)
                        else:
                            logger.warning(f"Skipping medicine due to lack of information: {medicine}")

                    return medicines
            else:
                logger.error(f"OpenFDA API error. Status: {response.status}")
        logger.warning(f"No medicines found for disease: {disease_name}")
        return None

    # ... rest of the methods ...


    async def get_rxnorm_info(self, drug_name):
        if drug_name == 'N/A':
            return None
        encoded_name = urllib.parse.quote(drug_name)
        url = f"{self.rxnorm_url}/drugs?name={encoded_name}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                elif 'application/xml' in content_type:
                    text = await response.text()
                    data = xmltodict.parse(text)
                else:
                    return None

                if 'drugGroup' in data and 'conceptGroup' in data['drugGroup']:
                    for group in data['drugGroup']['conceptGroup']:
                        if 'conceptProperties' in group:
                            props = group['conceptProperties']
                            if isinstance(props, list):
                                prop = props[0]
                            else:
                                prop = props
                            return {
                                'name': prop.get('name', 'N/A'),
                                'rxcui': prop.get('rxcui', 'N/A'),
                                'synonym': prop.get('synonym', 'N/A'),
                                'generic_name': await self.get_generic_name(prop.get('rxcui', 'N/A')),
                                'definition': await self.get_drug_definition(prop.get('rxcui', 'N/A'))
                            }
        return None

    async def get_generic_name(self, rxcui):
        if rxcui == 'N/A':
            return 'N/A'
        url = f"{self.rxnorm_url}/rxcui/{rxcui}/allrelated"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                elif 'application/xml' in content_type:
                    text = await response.text()
                    data = xmltodict.parse(text)
                else:
                    return 'N/A'

                if 'allRelatedGroup' in data:
                    for group in data['allRelatedGroup']['conceptGroup']:
                        if group['tty'] == 'IN':  # IN stands for Ingredient (generic)
                            return group['conceptProperties'][0]['name']
        return 'N/A'

    async def get_drug_definition(self, rxcui):
        if rxcui == 'N/A':
            return 'N/A'
        url = f"{self.rxnorm_url}/rxcui/{rxcui}/definition"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                elif 'application/xml' in content_type:
                    text = await response.text()
                    data = xmltodict.parse(text)
                else:
                    return 'N/A'

                if 'definitionGroup' in data and 'definition' in data['definitionGroup']:
                    definitions = data['definitionGroup']['definition']
                    if isinstance(definitions, list):
                        return definitions[0].get('definition', 'N/A')
                    elif isinstance(definitions, dict):
                        return definitions.get('definition', 'N/A')
        return 'N/A'

    async def get_dailymed_info(self, set_id):
        url = f"{self.dailymed_url}/spls/{set_id}.json"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if 'data' in data and 'spl' in data['data']:
                    spl = data['data']['spl']
                    return {
                        'name': spl.get('productNameList', [{}])[0].get('productName', 'N/A'),
                        'generic_name': spl.get('genericMedicineList', [{}])[0].get('genericMedicineName', 'N/A'),
                    }
        return None