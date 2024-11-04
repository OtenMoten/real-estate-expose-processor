import ast
import logging
from typing import List, Tuple
from flask import Flask, request, jsonify
import uuid
import threading

from jinja2 import Environment, FileSystemLoader

from config import Config
from services.gpt_service import GPTService
from services.hubspot_service import HubspotService
from models import ListInfo, Contact, Company, KeyFacts, TaskResult
from task_manager import TaskManager
from util import Util

logger = logging.getLogger(__name__)


class Router:
    def __init__(self, app: Flask, config: Config):
        self.app = app
        self.config = config
        self.task_manager = TaskManager()
        self.hubspot_service = HubspotService(access_token=config.HUBSPOT_API_KEY)
        self.gpt_service = GPTService(config)
        self.util = Util(config)
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))
        self.setup_routes()

    def setup_routes(self):
        self.app.route('/', methods=['GET'])(self.index)
        self.app.route('/upload', methods=['POST'])(self.upload_file)
        self.app.route('/progress/<task_id>')(self.get_progress)

    def index(self):
        return self.render_template('upload.html')

    def upload_file(self):
        if 'file' not in request.files or not request.files['file'].filename:
            return jsonify({'error': 'No file selected'}), 400

        file = request.files['file']
        if file and self.util.allowed_file(file.filename):
            task_id = str(uuid.uuid4())
            pdf_content = file.read()
            threading.Thread(target=self.process_pdf_and_select_list, args=(task_id, pdf_content)).start()
            return jsonify({'task_id': task_id}), 202

        return jsonify({'error': 'Invalid file type'}), 400

    def get_progress(self, task_id):
        progress = self.task_manager.get_progress(task_id)

        if progress['percent'] == 100:
            results = self.task_manager.get_results(task_id)
            return jsonify({**progress, 'results': self.render_template('result.html', results=results)})

        return jsonify(progress)

    def process_pdf_and_select_list(self, task_id: str, pdf_content: bytes):
        try:
            self.task_manager.update_progress(task_id, "Extracting text from PDF...", 10)
            text = self.util.extract_text_from_pdf(pdf_content)

            if not text:
                raise ValueError("Failed to extract text from PDF")

            key_facts = self.extract_key_facts(task_id, text)
            selected_list_name, selected_list_id = self.select_list(task_id, text)
            contacts, companies = self.get_members(task_id, selected_list_id)

            curated_member = ""

            if len(contacts) > 0:
                curated_member = self.curate_member(task_id, "; ".join(f"{contact.firstname}{contact.lastname}" for contact in contacts))
            elif len(companies) > 0:
                curated_member = self.curate_member(task_id, "; ".join(f"{company.name}" for company in companies))

            curated_member = Util.string_to_list(curated_member)

            html_email = self.generate_email(task_id, text, selected_list_name)

            self.task_manager.update_progress(task_id, "Complete", 100)
            task_result = TaskResult(
                key_facts=key_facts,
                selected_list=selected_list_name,
                selected_list_id=selected_list_id,
                selected_contacts=contacts,
                selected_companies=companies,
                curated_member=curated_member,
                email=html_email
            )
            self.task_manager.set_results(task_id, task_result.model_dump())
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            self.task_manager.update_progress(task_id, f"Error: {str(e)}", 100)
            self.task_manager.set_results(task_id, TaskResult().model_dump())

    def extract_key_facts(self, task_id: str, text: str) -> KeyFacts:
        self.task_manager.update_progress(task_id, "Extracting key facts ...", 20)
        return self.gpt_service.extract_key_facts(text)

    def select_list(self, task_id: str, text: str) -> Tuple[str, str]:

        self.task_manager.update_progress(task_id, "Fetching all lists from HubSpot ...", 40)
        hubspot_lists: List[ListInfo] = self.hubspot_service.get_lists()

        self.task_manager.update_progress(task_id, "Analyze text and start selection of list with GPT...", 60)
        list_names = [a_list.name for a_list in hubspot_lists]
        selected_list_name = self.gpt_service.analyze_text_and_select_list(text, list_names)

        selected_list_id = next((a_list.listId for a_list in hubspot_lists
                                 if a_list.name.lower().strip() == selected_list_name.lower().strip()), None)

        return selected_list_name, selected_list_id

    def get_members(self, task_id: str, selected_list_id: str) -> Tuple[List[Contact], List[Company]]:
        self.task_manager.update_progress(task_id, "Getting details of list members from HubSpot ...", 70)

        member_ids = self.hubspot_service.get_members_by_list_id(selected_list_id)

        contacts = self.hubspot_service.get_contacts_details(member_ids)
        companies = self.hubspot_service.get_companies_details(member_ids)

        return contacts, companies

    def curate_member(self, task_id: str, text: str) -> str:
        self.task_manager.update_progress(task_id, "Curating top 25 performer ...", 80)
        members = self.gpt_service.curate_members(text)

        return members

    def generate_email(self, task_id: str, text: str, selected_list_name: str) -> str:
        self.task_manager.update_progress(task_id, "Generating email with GPT ...", 90)
        html_email = self.gpt_service.generate_email(text, selected_list_name)

        return html_email

    def render_template(self, template_name: str, **context) -> str:
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)


def create_routes(app: Flask, config: Config):
    Router(app, config)
