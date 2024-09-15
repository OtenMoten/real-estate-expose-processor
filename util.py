import io
import logging
from typing import Set, Optional
import PyPDF2
from config import Config

logger = logging.getLogger(__name__)


class PDFUtil:
    ALLOWED_EXTENSIONS: Set[str] = {'pdf'}

    @classmethod
    def allowed_file(cls, filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS

    @staticmethod
    def extract_text_from_pdf(pdf_content: bytes) -> Optional[str]:
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return "".join(page.extract_text() for page in pdf_reader.pages)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return None


class Util:
    def __init__(self, config: Config):
        self.config = config
        self.pdf_util = PDFUtil()

    def allowed_file(self, filename: str) -> bool:
        return self.pdf_util.allowed_file(filename)

    def extract_text_from_pdf(self, pdf_content: bytes) -> Optional[str]:
        return self.pdf_util.extract_text_from_pdf(pdf_content)

    @staticmethod
    def string_to_list(input_string):
        # Check if input is a string
        if not isinstance(input_string, str):
            raise TypeError("Input must be a string")

        # Remove leading/trailing whitespace
        input_string = input_string.strip()

        # Check if the string starts and ends with square brackets
        if not (input_string.startswith('[') and input_string.endswith(']')):
            raise ValueError("Input string must start with '[' and end with ']'")

        # Remove the square brackets
        cleaned_string = input_string[1:-1]

        # Split the string by comma, handling potential nested structures
        item_list = []
        current_item = ""
        nested_level = 0

        for char in cleaned_string:
            if char == ',' and nested_level == 0:
                if current_item:
                    item_list.append(current_item.strip())
                    current_item = ""
            else:
                if char == '(':
                    nested_level += 1
                elif char == ')':
                    nested_level -= 1
                current_item += char

        # Add the last item if there's any
        if current_item:
            item_list.append(current_item.strip())

        # Remove any empty strings from the list
        item_list = [item for item in item_list if item]

        return item_list
