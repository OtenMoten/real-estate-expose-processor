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
        You are an AI assistant tasked with extracting key facts from real estate exposés. 
        Extract the following information and return it in a JSON format:
        {
            "address": {
                "street": string,
                "house_number": string,
                "postal_code": string,
                "city": string,
                "population": number
            },
            "purchase_price": string,
            "usable_area": number,
            "plot_size": number,
            "residential_units": number,
            "rental_income": string,
            "wault": number
        }
        If a piece of information is not available, omit that field from the JSON.
        """
        user_content = (f"Exposé text: {text}\n\nPlease extract the key facts from this exposé and return them in the specified JSON format "
                        f"and without markdown tags/syntax (not beginning with ```json).")
        response = self._make_openai_request(prompt, user_content)
        json_data = self.parse_string_to_json(response)
        if json_data:
            address_data = json_data.pop('address', {})
            return KeyFacts(address=Address(**address_data), **json_data)
        return KeyFacts()  # Return an empty KeyFacts object if parsing fails

    def generate_email(self, text: str, name_of_list: str) -> str:
        prompt = (
            "You are an AI assistant tasked with writing fancy (using emojis) and modern (use trigger/buzzwords), "
            "but also very professional, emails (in German) for selling real estate properties, based on user input. "
            "Analyze the given text and name of the target audience."
        )
        user_content = (
            f"Exposé text: {text}\n\nList name: {name_of_list}\n\n"
            "Please analyze the exposé and generate a proper email for the target audience (list name). "
            "Important note: Respond with an HTML email only using MDBootstrap CSS classes "
            "(do not write custom style tags) and without markdown tags/syntax (not beginning with ```html)!"
        )
        return self._make_openai_request(prompt, user_content)

    def curate_members(self, text: str) -> str:
        prompt = (
            "You are an AI system that can analyse and evaluate a given list of companies or people from the German real estate industry."
            "\nProceed systematically and objectively. Consider only facts and reputable sources for your evaluation. "
            "Your task is to: "
            "\n1. Research each company/person in the list in terms of: - market presence (e.g. awareness, market share, media presence) "
            "in the German property industry - key financial figures such as sales and profit growth or total assets, if available "
            "\n2. Output top 25 list as in two brackets [a, b, d, ...] only without any other text, you message must start with '[' and and with ']'!"
            "The output should in the list formatted in two brackets [a, b, d, ...] only without any other text, you message must start with '[' and and with ']'."
        )
        user_content = (
            f"List of companies or persons: {text}\n\n"
            "Please analyze the list and return the top 25 performer in two brackets [a, b, d, ...] only without any other text, you message must start with '[' and and with ']'! "
            "Important note: Respond in list as in two brackets [a, b, d, ...] only without any other text, you message must start with '[' and and with ']' "
            "(do not write custom style tags) and without markdown tags/syntax (not beginning with ```json/html/or any other tag)!"
        )
        return self._make_openai_request(prompt, user_content)

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
