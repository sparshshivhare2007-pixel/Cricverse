from database.connection import db
from Assets.files import RUN_VIDEOS, ACHIEVE_VIDEOS

MEDIA_COLLECTION = "bot_media"

TYPE_MAP = {
    "0":         (RUN_VIDEOS,     "0"),
    "1":         (RUN_VIDEOS,     "1"),
    "2":         (RUN_VIDEOS,     "2"),
    "3":         (RUN_VIDEOS,     "3"),
    "4":         (RUN_VIDEOS,     "4"),
    "5":         (RUN_VIDEOS,     "5"),
    "6":         (RUN_VIDEOS,     "6"),
    "out":       (RUN_VIDEOS,     "Out"),
    "batting":   (RUN_VIDEOS,     "Batting"),
    "bowling":   (RUN_VIDEOS,     "Bowling"),
    "opening":   (RUN_VIDEOS,     "Opening"),
    "50":        (ACHIEVE_VIDEOS, 50),
    "100":       (ACHIEVE_VIDEOS, 100),
    "150":       (ACHIEVE_VIDEOS, 150),
    "250":       (ACHIEVE_VIDEOS, 250),
    "duck":      (ACHIEVE_VIDEOS, "Duck"),
    "3wkt":      (ACHIEVE_VIDEOS, 3),
    "5wkt":      (ACHIEVE_VIDEOS, 5),
    "hat_trick": (ACHIEVE_VIDEOS, "HAT_TRICK"),
}

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


async def add_media_file(type_key: str, file_id: str):
    await db.db[MEDIA_COLLECTION].update_one(
        {"type": type_key},
        {"$addToSet": {"file_ids": file_id}},
        upsert=True,
    )
    target_dict, dict_key = TYPE_MAP[type_key]
    lst = target_dict.get(dict_key)
    if lst is None:
        target_dict[dict_key] = [file_id]
    elif file_id not in lst:
        lst.append(file_id)


async def remove_media_file(type_key: str, file_id: str):
    await db.db[MEDIA_COLLECTION].update_one(
        {"type": type_key},
        {"$pull": {"file_ids": file_id}},
    )
    target_dict, dict_key = TYPE_MAP[type_key]
    lst = target_dict.get(dict_key)
    if lst and file_id in lst:
        lst.remove(file_id)


async def list_media_files(type_key: str):
    doc = await db.db[MEDIA_COLLECTION].find_one({"type": type_key})
    return doc.get("file_ids", []) if doc else []


async def load_all_media():
    async for doc in db.db[MEDIA_COLLECTION].find():
        type_key = doc.get("type")
        file_ids = doc.get("file_ids", [])
        if not type_key or type_key not in TYPE_MAP or not file_ids:
            continue
        target_dict, dict_key = TYPE_MAP[type_key]
        existing = target_dict.get(dict_key)
        if existing is None:
            target_dict[dict_key] = list(file_ids)
        else:
            for fid in file_ids:
                if fid not in existing:
                    existing.append(fid)
