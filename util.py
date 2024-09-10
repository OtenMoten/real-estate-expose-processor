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
