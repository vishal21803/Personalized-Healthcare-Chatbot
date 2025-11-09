import xml.etree.ElementTree as ET

class MedlinePlusAPI:
    BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"

    def __init__(self, session):
        self.session = session

    async def get_disease_info(self, disease_name):
        params = {
            "db": "healthTopics",
            "term": disease_name,
            "rettype": "brief",
            "retmax": "1"
        }
        try:
            async with self.session.get(self.BASE_URL, params=params) as response:
                response.raise_for_status()
                content = await response.text()
                
                root = ET.fromstring(content)
                
                error = root.find(".//error-msg")
                if error is not None:
                    return f"Error from MedlinePlus API: {error.text}"

                documents = root.findall(".//document")
                if documents:
                    title = documents[0].find(".//content[@name='title']")
                    summary = documents[0].find(".//content[@name='FullSummary']")
                    if title is not None and summary is not None:
                        return f"Title: {title.text}\nSummary: {summary.text}"
                    else:
                        return "Information found, but unable to extract details."
                else:
                    return "No specific information available for this condition."
        except Exception as e:
            return f"Unable to fetch information at this time. Error: {str(e)}"