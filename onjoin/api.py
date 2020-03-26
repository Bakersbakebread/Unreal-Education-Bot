from dataclasses import dataclass
import pandas as pd
from fuzzywuzzy import process, fuzz
import os

import logging
log = logging.getLogger("red.unreal.api")

path = os.path.dirname(os.path.abspath(__file__))
DATA = pd.read_json(path + "/school_list.json")
choices = DATA['name'].unique()


@dataclass()
class SearchResult:
    state_province: str
    country: str
    name: str
    alpha_code: str
    websites: list
    domains: list


async def school_fuzzy_search(query):
    log.info(f"Fuzzy searching school, query: {query}")
    possibilities = process.extract(query, choices,
                                    scorer=fuzz.token_sort_ratio)
    maybes = [possible for possible in possibilities if possible[1] >= 50][:5]
    log.info(f"{len(maybes)} results found")
    return maybes


async def parse_result(school_name: str):
    data = DATA.to_dict("records")
    result = [d for d in data if d['name'].lower() == school_name.lower()][0]
    return SearchResult(
        state_province=result.get("state-province"),
        country=result.get("country"),
        name=result.get("name"),
        alpha_code=result.get("alpha_two_code"),
        websites=result.get("web_pages"),
        domains=result.get("domains"),
    )
