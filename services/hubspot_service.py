import logging
from typing import List, Dict, Any, Type, TypeVar
import time
from tqdm import tqdm
import requests
from hubspot import HubSpot
from hubspot.crm.lists import ListSearchRequest
from hubspot.crm.lists.exceptions import ApiException
from models import HubSpotObjectBase, Contact, Company, ListInfo

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

T = TypeVar('T', Contact, Company)


class HubspotService:
    BASE_URL = "https://api.hubapi.com"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.hubspot = HubSpot(access_token=self.access_token)
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get_lists(self) -> List[ListInfo]:
        list_search_request = ListSearchRequest(offset=0, query="", count=0, additional_properties=[""])
        try:
            api_response = self.hubspot.crm.lists.list_app_api.do_search(list_search_request=list_search_request)
            return [ListInfo(name=list_info['name'], listId=list_info['list_id'])
                    for list_info in api_response.to_dict()["lists"]]
        except ApiException as e:
            logger.error(f"Exception when calling lists_api->do_search: {e}")
            return []

    def get_contacts_details(self, contact_ids: List[str]) -> List[Contact]:
        url = f"{self.BASE_URL}/crm/v3/objects/contacts/batch/read"
        return self._get_details(url, contact_ids, Contact)

    def get_companies_details(self, company_ids: List[str]) -> List[Company]:
        url = f"{self.BASE_URL}/crm/v3/objects/companies/batch/read"
        return self._get_details(url, company_ids, Company)

    def _get_details(self, url: str, ids: List[str], model: Type[T]) -> List[T]:
        all_items = []
        properties = list(HubSpotObjectBase.__annotations__.keys()) + [
            k for k in model.__annotations__.keys() if k not in HubSpotObjectBase.__annotations__
        ]

        with tqdm(total=len(ids), desc=f"Fetching {model.__name__} details", unit="item") as pbar:
            for i in range(0, len(ids), 100):
                batch = ids[i:i + 100]
                payload = {
                    "properties": properties,
                    "inputs": [{"id": item_id} for item_id in batch]
                }
                data = self._make_request("POST", url, json=payload)
                all_items.extend([
                    model(**{k: props.get(k, '') for k in properties})
                    for item in data['results']
                    if (props := item.get('properties', {}))
                ])
                pbar.update(len(batch))
                time.sleep(0.1)  # Respect rate limits
        return all_items

    def get_members_by_list_id(self, list_id: str) -> List[str]:
        logger.info(f"Fetching members for list {list_id}...")
        member_ids = self._get_list_members(list_id)
        logger.info(f"Found {len(member_ids)} members in the list.")
        return member_ids

    def _get_list_members(self, list_id: str) -> List[str]:
        url = f"{self.BASE_URL}/crm/v3/lists/{list_id}/memberships"
        all_members = []
        with tqdm(desc="Fetching list members", unit="page") as pbar:
            while url:
                data = self._make_request("GET", url)
                all_members.extend(data['results'])
                url = data.get('paging', {}).get('next', {}).get('link')
                if url:
                    time.sleep(0.1)  # Respect rate limits
                pbar.update(1)
        return [member['recordId'] for member in all_members]

    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise ApiException(f"API request failed: {str(e)}")
