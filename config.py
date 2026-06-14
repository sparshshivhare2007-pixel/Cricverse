import os


class Config:
    # Telegram API
    API_ID = int(os.getenv("API_ID", "25887786"))
    API_HASH = os.getenv("API_HASH", "e4201277f5f2883f22c150167bd24479")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8970942794:AAGmRa84TEAB28xFB7Y7llvvSt0A5HtColk")

    # Database
    MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://clone1legacy:Vinit.123@clone1.sj89zbp.mongodb.net/?appName=clone1")

    # Bot Info
    BOT_USERNAME = os.getenv("BOT_USERNAME", "@CricketLegacy2Bot")
    SUPPORT_GROUP = os.getenv(
        "SUPPORT_GROUP",
        "https://t.me/+joF1bCfiMT9jMzVh"
    )
    PLAY_ZONE_INFO = os.getenv(
        "PLAY_ZONE_INFO",
        "https://t.me/+joF1bCfiMT9jMzVh"
    )

    # Owners
    OWNER_IDS = {
        int(x)
        for x in os.getenv("OWNER_IDS", "8186068163 1035382935").split()
    }

    # GitHub
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    UPSTREAM_REPO = os.getenv(
        "UPSTREAM_REPO",
        "https://github.com/drexocoder-source/Cricsssketlegssacys"
    )

    # AI / NVIDIA
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")

    # Images
    START_IMAGE = os.getenv(
        "START_IMAGE",
        "https://graph.org/file/a37d935e98e4c92e04cee-c1871cfafb3f808563.jpg"
    )

    # Logs
    LOG_CHANNEL = int(
        os.getenv("LOG_CHANNEL", "-1003692127639")
    )
