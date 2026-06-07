import logging

import aiohttp

logger = logging.getLogger(__name__)

_CITY_KEYS = ("city", "town", "village", "municipality", "county", "state")


async def get_city_from_coordinates(latitude: float, longitude: float) -> str | None:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "accept-language": "ru",
    }
    headers = {"User-Agent": "MentorlyBot/1.0"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                address = data.get("address", {})
                for key in _CITY_KEYS:
                    if city := address.get(key):
                        return city
                return None
    except Exception:
        logger.exception("Geocoding failed for %s, %s", latitude, longitude)
        return None
