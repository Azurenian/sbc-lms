"""
Handles Payload CMS integration for uploading media files.
"""

import requests
import os
import json

def upload_media(file_path: str, media_type: str = "audio", alt: str = None, auth_token: str = None) -> dict:
    """
    Uploads a media file (audio/video) to Payload CMS via REST API.
    Always returns the raw media object as returned by Payload CMS (no Lexical node wrapping).
    """
    PAYLOAD_BASE_URL = os.getenv("PAYLOAD_BASE_URL", "http://localhost:3000")
    PAYLOAD_CMS_URL = f"{PAYLOAD_BASE_URL}/api/media"
    # Use provided auth_token or fallback to environment variable
    token = auth_token or os.getenv("PAYLOAD_CMS_TOKEN")
    headers = {"Authorization": f"JWT {token}"} if token else {}
    with open(file_path, "rb") as f:
        files = {
            "file": (os.path.basename(file_path), f, f"{media_type}/mp4" if media_type == "video" else "audio/mp3")
        }
        data = {
            "_payload": json.dumps({"alt": alt})
        }
        response = requests.post(PAYLOAD_CMS_URL, files=files, data=data, headers=headers)
        response.raise_for_status()
        return response.json()

def upload_lesson(lesson_data: dict, auth_token: str = None) -> dict:
    """
    Uploads the lesson JSON to Payload CMS via REST API.
    Returns the response from Payload CMS (e.g., lesson ID, etc.).
    """
    PAYLOAD_BASE_URL = os.getenv("PAYLOAD_BASE_URL", "http://localhost:3000")
    PAYLOAD_CMS_LESSON_URL = f"{PAYLOAD_BASE_URL}/api/lessons"
    # Use provided auth_token or fallback to environment variable
    token = auth_token or os.getenv("PAYLOAD_CMS_TOKEN")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"JWT {token}"
    
    response = requests.post(PAYLOAD_CMS_LESSON_URL, headers=headers, json=lesson_data)
    response.raise_for_status()
    return response.json()
