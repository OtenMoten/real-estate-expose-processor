from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


@dataclass
class HubSpotObjectBase:
    hs_object_id: str
    createdate: str
    lastmodifieddate: str
    lifecycle_stage: str
    associations: str = ""


@dataclass
class Contact(HubSpotObjectBase):
    email: str = ""
    firstname: str = ""
    lastname: str = ""


@dataclass
class Company(HubSpotObjectBase):
    name: str = ""


class ListInfo(BaseModel):
    name: str
    listId: str


class Address(BaseModel):
    street: Optional[str] = Field(default="missing")
    house_number: Optional[str | int] = Field(default="missing")
    postal_code: Optional[str | int] = Field(default="missing")
    city: Optional[str] = Field(default="missing")
    population: Optional[int | str] = Field(default="missing")


class KeyFacts(BaseModel):
    address: Address = Field(default_factory=Address)
    purchase_price: Optional[int | float | str] = Field(default="missing")
    price_per_square: Optional[int | float | str] = Field(default="missing")
    usable_area: Optional[int | float | str] = Field(default="missing")
    plot_size: Optional[int | float | str] = Field(default="missing")
    residential_units: Optional[int | float | str] = Field(default="missing")
    rental_income: Optional[int | float | str] = Field(default="missing")
    wault: Optional[int | float | str] = Field(default="missing")


class TaskProgress(BaseModel):
    status: str
    percent: int


class TaskResult(BaseModel):
    key_facts: Optional[KeyFacts] = Field(default_factory=KeyFacts)
    selected_list: Optional[str] = Field(default="")
    selected_list_id: Optional[str] = Field(default="")
    selected_contacts: List[Contact] = Field(default_factory=list)
    selected_companies: List[Company] = Field(default_factory=list)
    curated_member: List[str] = Field(default_factory=list)
    email: Optional[str] = Field(default="")
