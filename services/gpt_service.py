import json
import logging
from typing import Dict, List, Union, Any
import httpx
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai import (
    APIError,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
    InternalServerError,
)

from config import Config
from models import KeyFacts, Address

logger = logging.getLogger(__name__)


class GPTService:
    def __init__(self, config: Config):
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=httpx.Timeout(30.0, connect=15.0),
            max_retries=3,
        )
        self.model = "gpt-4o"
        self.max_tokens = 128000

    def analyze_text_and_select_list(self, text: str, list_names: List[str]) -> str:
        prompt = (
            "You are an AI assistant tasked with analyzing real estate exposés and matching them to the most "
            "appropriate list based on the content. Analyze the given text and select the best matching list "
            "from the provided options. Respond with only the name of the selected list."
        )
        user_content = f"Exposé text: {text}\n\nAvailable lists: {', '.join(list_names)}"
        return self._make_openai_request(prompt, user_content)

    def extract_key_facts(self, text: str) -> KeyFacts:
        prompt = """
        You are an expert real estate data extraction specialist, fluent in both German and English. Your task is to meticulously analyze real estate exposés in either language and extract ALL relevant information. Follow these comprehensive search patterns:

        1. DETAILED SEARCH PATTERNS (GERMAN/ENGLISH):

        Purchase Price / Kaufpreis:
        - German: 
            * "Kaufpreis", "Preis", "Angebotspreis", "Verkaufspreis", "Investment", "Verkauf für", "zum Preis von"
            * "Kaufsumme", "Gesamtpreis", "Objektpreis", "Investitionssumme", "Mindestpreis"
            * "VB", "VHB", "auf Anfrage", "Verhandlungsbasis"
            * "Gesamtinvestition", "Gesamtvolumen", "Kaufoption"
            * "Kaufpreisfaktor", "Anschaffungskosten"
        - English: 
            * "purchase price", "price", "asking price", "sales price", "investment", "for sale at"
            * "total price", "property price", "investment sum", "minimum price"
            * "price on request", "POA", "guide price", "offers over"
            * "total investment", "acquisition cost", "purchase option"
            * "purchase price factor", "cost of acquisition"

        Areas / Flächen:
        Usable Area / Nutzfläche:
        - German:
            * "Nutzfläche", "Wohnfläche", "Gesamtfläche", "vermietbare Fläche", "Mietfläche"
            * "Gewerbefläche", "Bürofläche", "Ladenfläche", "Verkaufsfläche"
            * "BGF", "Bruttogrundfläche", "NGF", "Nettogrundfläche"
            * "vermietbare Fläche", "Nutzungseinheit", "Gewerbeeinheit"
            * "Wohn- und Nutzfläche", "Wohn-/Nutzfläche"
            * "Hauptnutzfläche", "Nebennutzfläche", "Funktionsfläche"
        - English:
            * "usable area", "living space", "total area", "lettable area", "rental space"
            * "commercial space", "office space", "retail space", "sales floor"
            * "GFA", "gross floor area", "NFA", "net floor area"
            * "leasable area", "usable unit", "commercial unit"
            * "living and usable space", "total usable space"
            * "main usable area", "auxiliary area", "functional area"

        Plot Size / Grundstücksfläche:
        - German:
            * "Grundstücksfläche", "Grundstück", "Grundstücksgröße", "Flurstück"
            * "Gesamtgrundstück", "Grundfläche", "Außenfläche", "Freifläche"
            * "Bauplatz", "Bauland", "Baugrundstück", "Geländefläche"
            * "Parkplatzfläche", "Gartenfläche", "Hoffläche"
            * "Grundstücksanteil", "Flurstückgröße"
        - English:
            * "plot size", "land area", "property size", "lot size"
            * "total plot", "ground area", "outdoor area", "open space"
            * "building plot", "construction site", "development land"
            * "parking area", "garden area", "courtyard area"
            * "land share", "plot dimensions"

        Address / Adresse:
        - German:
            * "Lage", "Standort", "gelegen in", "befindet sich in"
            * "-straße", "-weg", "-allee", "-platz", "-ring", "-damm", "-ufer"
            * "Hausnummer", "Nr.", "Nummer", "Postleitzahl", "PLZ"
            * "Stadtbezirk", "Stadtteil", "Ortsteil", "Quartier"
            * "im Herzen von", "zentral gelegen", "direkt an"
            * "Anschrift", "Adresse", "Objektstandort"
        - English:
            * "location", "situated in", "located at", "address"
            * "street", "road", "avenue", "plaza", "ring", "lane", "boulevard"
            * "house number", "no.", "number", "postal code", "zip code"
            * "district", "quarter", "neighborhood", "area"
            * "in the heart of", "centrally located", "directly at"
            * "property location", "site address"

        Rental Income / Mieteinnahmen:
        - German:
            * "Mieteinnahmen", "Jahresmiete", "Monatsmiete", "Nettokaltmiete"
            * "Ist-Miete", "Mietertrag", "Sollmiete", "Mietrendite"
            * "Jahresnettomiete", "Nettomieteinnahmen", "Mieteinnahmen p.a."
            * "Mietzins", "Pachteinnahmen", "Ertrag p.a."
            * "Jahresrohertrag", "Jahresmietertrag", "Mietrendite"
            * "Kaltmiete", "Warmmiete", "Betriebskosten"
        - English:
            * "rental income", "annual rent", "monthly rent", "net rent"
            * "current rent", "rental yield", "target rent", "rental return"
            * "annual net rent", "net rental income", "rental income p.a."
            * "lease income", "rental earnings", "yield p.a."
            * "gross annual income", "annual rental income", "rental yield"
            * "net cold rent", "gross rent", "operating costs"

        Residential Units / Wohneinheiten:
        - German:
            * "Wohneinheiten", "Einheiten", "Wohnungen", "Gewerbeeinheiten"
            * "Appartements", "Wohn- und Geschäftseinheiten"
            * "Zimmer", "Räume", "Raumeinheiten", "Nutzungseinheiten"
            * "Gewerbeflächen", "Laden", "Geschäfte", "Büros"
            * "Stellplätze", "Tiefgaragenplätze", "Parkplätze"
            * "Wohnungsmix", "Einheitenaufteilung"
        - English:
            * "residential units", "units", "apartments", "commercial units"
            * "flats", "residential and commercial units"
            * "rooms", "spaces", "room units", "usage units"
            * "commercial spaces", "shops", "stores", "offices"
            * "parking spaces", "underground parking", "parking lots"
            * "unit mix", "unit distribution"

        WAULT:
        - German:
            * "durchschnittliche Mietvertragslaufzeit", "gewichtete Restlaufzeit"
            * "WAULT", "Mietvertragslaufzeit", "Restlaufzeit der Mietverträge"
            * "durchschnittliche Restlaufzeit", "gewichtete durchschnittliche Laufzeit"
            * "verbleibende Mietdauer", "Laufzeit der Mietverträge"
            * "mittlere gewichtete Mietvertragsdauer"
        - English:
            * "weighted average unexpired lease term", "average lease duration"
            * "WAULT", "lease term", "remaining lease term"
            * "weighted average lease term", "average unexpired term"
            * "remaining rental period", "duration of lease agreements"
            * "mean weighted lease duration"

        2. NUMBER AND UNIT FORMATS:
        - German number format: 1.234,56
        - English number format: 1,234.56
        - Area units: m², qm, Quadratmeter, square meters, sq m, sq. m.
        - Currency formats: 
            * "1.234.567 €", "1.234.567,00 €", "EUR 1.234.567"
            * "1,234,567 €", "1,234,567.00 €", "€1,234,567"
            * "T€" (Tausend Euro), "Mio. €" (Millionen Euro)
            * "k€" (thousand euros), "m€" (million euros)
            * "TEUR", "Mio. EUR", "Millionen Euro"

        3. EXTRACTION METHODOLOGY:
        - Analyze the entire document multiple times, focusing on different data types each time
        - Check both headers and body text
        - Look for information in tables, lists, and continuous text
        - Consider both formal terms and colloquial expressions
        - Process ALL numbers that appear with relevant units
        - Check for information in both languages within the same document
        - Look for population data near city names or in location descriptions
        - Consider variations in formatting and spelling
        - Check for information in footnotes and annotations

        4. DATA STANDARDIZATION RULES:
        - Convert all areas to square meters (m²)
        - Standardize currency to Euro format with dots (1.234.567 €)
        - Ensure postal codes are 5 digits for German addresses
        - Convert any monthly rents to annual figures
        - Standardize WAULT to years if given in months

        Return in JSON format:
        {
            "address": {
                "street": string,        # Straße/Street
                "house_number": string,  # Hausnummer/House number
                "postal_code": string,   # PLZ/Postal code
                "city": string,         # Stadt/City
                "population": number    # Einwohner/Population
            },
            "purchase_price": string,   # Kaufpreis/Purchase price
            "price_per_square": string,   # Kaufpreis pro Quadratmeter/Purchase price per square
            "usable_area": number,     # Nutzfläche/Usable area (in m²)
            "plot_size": number,       # Grundstücksfläche/Plot size (in m²)
            "residential_units": number, # Wohneinheiten/Residential units
            "rental_income": string,    # Mieteinnahmen/Rental income
            "wault": number            # Gewichtete Restlaufzeit/WAULT (in years)
        }

        IMPORTANT:
        - Analyze the text iteratively to ensure no information is missed
        - Convert all values to the specified formats before returning
        - If information appears multiple times, use the most detailed/recent version
        - Include all found information, even if some fields are uncertain
        - Pay special attention to context when extracting numbers
        - Consider both abbreviated and full forms of measurements
        """

        user_content = (
            f"Exposé text: {text}\n\n"
            f"Please analyze this text thoroughly in both German and English using the specified methodology. "
            f"Extract ALL possible information, even if you're not completely certain about some values. "
            f"Pay special attention to different number formats and units in both languages. "
            f"Return the data in the specified JSON format without any additional explanation or markdown."
        )

        response = self._make_openai_request(prompt, user_content)
        json_data = self.parse_string_to_json(response)
        if json_data:
            address_data = json_data.pop('address', {})
            return KeyFacts(address=Address(**address_data), **json_data)
        return KeyFacts()

    def generate_email(self, text: str, name_of_list: str) -> str:
        prompt = (
            "You are an AI assistant specialized in creating high-converting real estate marketing emails in German. "
            "Guidelines:\n"
            "1. Tone: Professional yet approachable (70% formal, 30% modern)\n"
            "2. Style Elements:\n"
            "   - Use 2-3 relevant emojis per section (property features, benefits, call-to-action)\n"
            "   - Include or transform modern buzzwords from the user input\n"
            "3. Email Structure:\n"
            "   - Attention-grabbing subject line (max 50 chars)\n"
            "   - Preview text (max 100 chars)\n"
            "   - Personalized greeting\n"
            "   - 2-3 key property highlights\n"
            "   - Value proposition\n"
            "   - Clear call-to-action\n"
            "   - Professional closing\n"
            "4. Length: 150-250 words total\n"
            "5. Must include: Property price, location benefits, unique selling points"
        )

        user_content = (
            f"Exposé text: {text}\n\n"
            f"Target Audience List: {name_of_list}\n\n"
            "Requirements:\n"
            "1. Generate a complete email following the structure above\n"
            "2. Adapt tone and content for the specific target audience\n"
            "3. Include a compelling call-to-action for property viewing\n"
            "4. Format using MDBootstrap CSS classes only\n"
            "5. Return complete <body> tag content (no custom CSS/JS/imports)\n"
            "6. No markdown syntax or ```html tags"
        )
        return self._make_openai_request(prompt, user_content)

    def curate_members(self, text: str, attempts: int = 0) -> str:
        if attempts >= 3:
            return "['ERROR']"

        prompt = (
            "You are a precise data formatting system with specific output requirements."
            "\n\nINPUT ANALYSIS RULES:"
            "\n1. Analyze German real estate entities for:"
            "\n   - Market presence (AUM, transaction volume, market share)"
            "\n   - Financial metrics (revenue, growth rate, profitability)"
            "\n   - Industry influence (reputation, partnerships, innovation)"
            "\n2. Select top performers (maximum 25)"
            "\n3. Important:"
            "\n   - Keep company suffixes (GmbH, AG, etc.) with their companies"
            "\n   - Keep L.P., S.à r.l. etc. as part of company names"
            "\n   - Use official company names"
            "\n\nCRITICAL OUTPUT REQUIREMENTS:"
            "\n- MUST return ONLY a comma-separated list"
            "\n- NO quotes, brackets, or special characters"
            "\n- NO explanations or additional text"
            "\n- NO formatting or markdown"
            "\n- NO spaces before/after commas"
            "\n- Company names exactly as provided"
            "\n\nCORRECT EXAMPLE:"
            "\nDeutsche Bank AG,Vonovia SE,AEW Capital Management L.P."
            "\n\nINCORRECT EXAMPLES:"
            "\n❌ [Deutsche Bank, Vonovia]"
            "\n❌ Deutsche Bank L.P., Management"  # split company name
            "\n❌ \"Deutsche Bank\", \"Vonovia\""
            "\n❌ Here are the companies: Deutsche Bank, Vonovia"
            "\n\nVIOLATION OF THESE RULES WILL CAUSE SYSTEM FAILURE"
        )

        user_content = (
            f"ENTITIES TO ANALYZE: {text}\n"
            "\nRETURN FORMAT: entity1,entity2,entity3"
            "\nIMPORTANT: Keep company legal forms (GmbH, AG, L.P., etc.) together with company names!"
        )

        try:
            response = self._make_openai_request(prompt, user_content)

            # Basic input validation
            if not response.strip():
                raise ValueError("Empty response received")

            # Split and clean items
            items = [item.strip() for item in response.split(',') if item.strip()]

            # Validate item count
            if len(items) > 25:
                items = items[:25]
            elif not items:
                raise ValueError("No valid items found")

            # New validation system
            for item in items:

                # 1. Check for minimum length
                if len(item) < 2:
                    raise ValueError(f"Company name too short: {item}")

                # 2. Check for invalid characters
                invalid_chars = '[]\'"<>{}'  # Add more if needed
                if any(char in invalid_chars for char in item):
                    raise ValueError(f"Invalid characters in company name: {item}")

                # 3. Check for common formatting issues
                if item.count('  ') > 0:  # Multiple spaces
                    raise ValueError(f"Multiple consecutive spaces in: {item}")
                if item.startswith(' ') or item.endswith(' '):
                    raise ValueError(f"Leading/trailing spaces in: {item}")

            # Construct final response
            final_response = '[' + ','.join(f'{item}' for item in items) + ']'

            # 4. Final structure validation
            if not final_response.startswith('[') or not final_response.endswith(']'):
                raise ValueError("Invalid list structure")

            if final_response.count('[') != 1 or final_response.count(']') != 1:
                raise ValueError("Multiple brackets detected")

            return final_response

        except ValueError as e:
            if attempts < 2:
                print(f"Attempt {attempts + 1} failed: {str(e)}")
            return self.curate_members(text, attempts + 1)
        except Exception as e:
            print(f"Critical error: {str(e)}")
            return "['ERROR']"

    def _make_openai_request(self, system_content: str, user_content: str) -> str:

        try:
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content}
                ],
                # max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except (RateLimitError, APIConnectionError, InternalServerError, APIStatusError, APIError) as e:
            logger.error(f"Error in OpenAI API request: {str(e)}")
            return ""

    @staticmethod
    def parse_string_to_json(input_string: str) -> Union[Dict[str, Any], List[Any], None]:
        def clean_string(s: str) -> str:
            import re
            s = s.strip()
            s = s.replace("'", '"')
            s = re.sub(r'(\w+)(?=\s*:)', r'"\1"', s)
            return s

        try:
            return json.loads(input_string)
        except json.JSONDecodeError:
            try:
                cleaned_string = clean_string(input_string)
                return json.loads(cleaned_string)
            except json.JSONDecodeError:
                try:
                    wrapped_string = f"[{clean_string(input_string)}]"
                    parsed_list = json.loads(wrapped_string)
                    return parsed_list[0] if len(parsed_list) == 1 else parsed_list
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON: {input_string}")
                    return None
