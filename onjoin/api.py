import aiohttp
from dataclasses import dataclass, field

API_BASE = "http://universities.hipolabs.com"
API_SEARCH = f"{API_BASE}/search?name="


@dataclass()
class SearchResult:
    state_province: str
    country: str
    name: str
    alpha_code: str
    websites: list
    domains: list


async def _search(query):
    session = aiohttp.ClientSession()
    async with session.get(f"{API_SEARCH}{query}") as response:
        json = await response.json()
        return json


async def _parse_result(results: dict):
    to_return = []
    for d in results:
        r = SearchResult(
            state_province=d.get("state-province"),
            country=d.get("country"),
            name=d.get("name"),
            alpha_code=d.get("alpha_two_code"),
            websites=d.get("web_pages"),
            domains=d.get("domains"),
        )
        to_return.append(r)

    return to_return


async def find_and_parse(query):
    results = await _search(query)
    return await _parse_result(results)
