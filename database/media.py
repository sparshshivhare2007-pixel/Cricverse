import random
from database.connection import db

MEDIA_COLLECTION = "bot_media"

_MEDIA_CACHE: dict = {}

TYPE_LABELS = {
    "0":         "Dot Ball (0)",
    "1":         "1 Run",
    "2":         "2 Runs",
    "3":         "3 Runs",
    "4":         "4 Runs (Boundary)",
    "5":         "5 Runs",
    "6":         "6 Runs (Six)",
    "out":       "Wicket / OUT",
    "batting":   "Batting Prompt",
    "bowling":   "Bowling Prompt",
    "opening":   "Match Opening",
    "50":        "Achievement: 50 Runs",
    "100":       "Achievement: 100 Runs",
    "150":       "Achievement: 150 Runs",
    "250":       "Achievement: 250 Runs",
    "duck":      "Achievement: Duck",
    "3wkt":      "Achievement: 3 Wickets",
    "5wkt":      "Achievement: 5 Wickets",
    "hat_trick": "Achievement: Hat-Trick",
}

ALL_TYPES = list(TYPE_LABELS.keys())

_ACHIEVE_KEY_MAP = {
    "BAT_50": "50",   "BAT_100": "100",  "BAT_150": "150",  "BAT_250": "250",
    "BOWL_3": "3wkt", "BOWL_5":  "5wkt",
    "HAT_TRICK": "hat_trick", "DUCK": "duck",
    50: "50", 100: "100", 150: "150", 250: "250",
    3: "3wkt", 5: "5wkt",
    "Duck": "duck", "HAT_TRICK": "hat_trick",
}


def _normalize(key) -> str:
    return str(key).lower()


def get_uploaded_video(key) -> str | None:
    files = _MEDIA_CACHE.get(_normalize(key), [])
    return random.choice(files) if files else None


def get_uploaded_achieve(achieve_key) -> str | None:
    canon = _ACHIEVE_KEY_MAP.get(achieve_key)
    if not canon:
        return None
    files = _MEDIA_CACHE.get(canon, [])
    return random.choice(files) if files else None


def has_uploaded(key) -> bool:
    return bool(_MEDIA_CACHE.get(_normalize(key)))


async def add_media_file(type_key: str, file_id: str):
    type_key = _normalize(type_key)
    await db.db[MEDIA_COLLECTION].update_one(
        {"type": type_key},
        {"$addToSet": {"file_ids": file_id}},
        upsert=True,
    )
    lst = _MEDIA_CACHE.setdefault(type_key, [])
    if file_id not in lst:
        lst.append(file_id)


async def remove_media_file(type_key: str, file_id: str):
    type_key = _normalize(type_key)
    await db.db[MEDIA_COLLECTION].update_one(
        {"type": type_key},
        {"$pull": {"file_ids": file_id}},
    )
    lst = _MEDIA_CACHE.get(type_key, [])
    if file_id in lst:
        lst.remove(file_id)


async def list_media_files(type_key: str):
    type_key = _normalize(type_key)
    return list(_MEDIA_CACHE.get(type_key, []))


async def load_all_media():
    _MEDIA_CACHE.clear()
    async for doc in db.db[MEDIA_COLLECTION].find():
        type_key = _normalize(doc.get("type", ""))
        file_ids = doc.get("file_ids", [])
        if type_key and file_ids:
            _MEDIA_CACHE[type_key] = list(file_ids)
    print(f"✅ Loaded custom media: {len(_MEDIA_CACHE)} type(s) with files")
