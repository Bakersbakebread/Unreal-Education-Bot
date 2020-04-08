from dataclasses import dataclass
import pandas as pd
from fuzzywuzzy import process, fuzz
import os

import logging
log = logging.getLogger("red.unreal.api")

path = os.path.dirname(os.path.abspath(__file__))
DATA = pd.read_json(path + "/school_list.json")
CHOICES = DATA['name'].unique()


async def school_fuzzy_search(query: str, config_choices: list):
    log.info(f"Fuzzy searching school, query: {query}")
    choices = list(CHOICES) + config_choices
    possibilities = process.extract(query, choices,
                                    scorer=fuzz.token_sort_ratio)
    # 1st is name 2nd index is the probability
    maybes = [possible for possible in possibilities if possible[1] >= 50][:5]
    log.info(f"{len(maybes)} results found")
    return maybes
