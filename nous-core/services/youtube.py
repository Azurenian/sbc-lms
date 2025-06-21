"""
Handles YouTube API integration for searching and downloading videos.
"""


from googleapiclient.discovery import build
import os
import yt_dlp

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Set this in your environment
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def search_videos(keywords: list, max_results: int = 10) -> list:
    """
    Searches YouTube for videos matching the given keywords.
    Returns a list of dicts: {title, videoId, thumbnail, url}
    """
    query = " ".join(keywords)
    youtube = build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        developerKey=YOUTUBE_API_KEY
    )
    search_response = youtube.search().list(
        q=query,
        part="id,snippet",
        maxResults=max_results,
        type="video"
    ).execute()

    results = []
    for item in search_response.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        results.append({
            "videoId": video_id,
            "title": snippet["title"],
            "thumbnail": snippet["thumbnails"]["high"]["url"],
            "channel": snippet.get("channelTitle", "Unknown Channel"),
            "duration": "Unknown",  # Would need additional API call to get duration
            "views": "Unknown",     # Would need additional API call to get view count
            "url": f"https://www.youtube.com/watch?v={video_id}"
        })
    return results

def download_video(url: str, out_path: str) -> str:
    """
    Downloads a YouTube video to the specified path using yt-dlp.
    Returns the path to the downloaded video file.
    """
    ydl_opts = {
        'outtmpl': out_path,
        # Use best available format with audio, fallback to lower quality if needed
        'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'quiet': False,  # Enable output to see what's happening
        'no_warnings': False,
        'extract_flat': False,
        # Additional options to handle extraction issues
        'writesubtitles': False,
        'writeautomaticsub': False,
        'ignoreerrors': True,
        # Try to get the best audio quality
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        # Handle geo-restrictions and age-gating
        'geo_bypass': True,
        'age_limit': 99,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First, extract info to check if video is available
            info = ydl.extract_info(url, download=False)
            print(f"Video info extracted: {info.get('title', 'Unknown')}")
            
            # Now download
            ydl.download([url])
            print(f"Successfully downloaded video to: {out_path}")
            
    except Exception as e:
        print(f"Error downloading video {url}: {e}")
        # Try with a simpler format as fallback
        fallback_opts = {
            'outtmpl': out_path,
            'format': 'worst[ext=mp4]/worst',
            'quiet': True,
            'ignoreerrors': True,
        }
        try:
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                ydl.download([url])
                print(f"Downloaded with fallback format to: {out_path}")
        except Exception as fallback_error:
            print(f"Fallback download also failed: {fallback_error}")
            raise e
    
    return out_path
