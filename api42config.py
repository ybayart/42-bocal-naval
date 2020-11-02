# coding=utf-8
import os

LOGIN = "jpeg"
TOKEN_URL = "https://api.intra.42.fr/oauth/token"
ENDPOINT = "https://api.intra.42.fr/v2"
RAISE=False
VERBOSE=True
PROGRESS_BAR = True
PER_PAGE = 100

PARAMS = {
    "client_id": os.environ.get("API_CLIENT"),
    "client_secret": os.environ.get("API_SECRET"),
    "grant_type": "client_credentials",
    "scope": "public projects tig forum profile elearning"
}

