from fastapi import FastAPI, UploadFile, File, Form, Body, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pathlib
import json
import os
import re
from datetime import datetime
from services import etts, gemini, youtube, payload
from services.chatbot import ChatbotService
from services.llm import get_llm_service
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio

load_dotenv()

app = FastAPI()

# Get CORS origins from environment variable
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:8081,http://localhost:3000,http://localhost:8000").split(",")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"WebSocket disconnected for session: {session_id}")

    async def send_progress_update(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(data)
            except Exception as e:
                print(f"Failed to send progress update to {session_id}: {e}")
                self.disconnect(session_id)

manager = ConnectionManager()

# Initialize chatbot service
chatbot_service = ChatbotService()
llm_service = get_llm_service()

# Function to load foundation prompt
def load_foundation_prompt():
    try:
        config_path = pathlib.Path("config/prompts.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("foundation_prompt", "")
        else:
            print("Warning: prompts.json not found, using fallback prompt")
            return "Create a comprehensive educational lesson from the provided PDF content."
    except Exception as e:
        print(f"Error loading foundation prompt: {e}")
        return "Create a comprehensive educational lesson from the provided PDF content."

async def generate_lesson_task(
    session_id: str,
    temp_path: pathlib.Path,
    title: str,
    course_id: int,
    auth_token: str,
    prompt: str
):
    try:
        # 1. Gemini: PDF to Lexical JSON
        await update_progress(session_id, "processing", 10, "Analyzing PDF content...")
        try:
            lexical_children = gemini.pdf_to_lexical(str(temp_path), prompt)
            if isinstance(lexical_children, str):
                lexical_children = json.loads(lexical_children)
            await update_progress(session_id, "processing", 40, "PDF content analysis complete")
        except Exception as e:
            await update_progress(session_id, "error", 100, f"AI content analysis failed: {str(e)}")
            return

        # 2. Gemini: Generate narration and keywords
        await update_progress(session_id, "processing", 40, "Generating audio narration script...")
        try:
            narration = gemini.lexical_to_narration(lexical_children)
            await update_progress(session_id, "processing", 55, "Audio narration script generated")
        except Exception as e:
            await update_progress(session_id, "error", 100, f"Audio narration script generation failed: {str(e)}")
            return

        await update_progress(session_id, "processing", 55, "Extracting keywords...")
        try:
            keywords = gemini.get_keywords(lexical_children)
            await update_progress(session_id, "processing", 70, "Keywords extracted successfully")
        except Exception as e:
            keywords = ["education", "learning", title.lower()]
            await update_progress(session_id, "processing", 70, "Keywords extracted (fallback)")

        # 3. YouTube: Auto-search for videos
        await update_progress(session_id, "youtube", 70, "Searching for relevant videos...")
        try:
            youtube_videos = youtube.search_videos(keywords, max_results=10)
            await update_progress(session_id, "youtube", 80, f"Found {len(youtube_videos)} educational videos")
        except Exception as e:
            youtube_videos = []
            await update_progress(session_id, "youtube", 80, "Video search completed (0 found or error)")

        # 4. Edge TTS: Generate audio narration
        await update_progress(session_id, "youtube", 80, "Generating audio narration file...")
        audio_path = None
        try:
            audio_dir = pathlib.Path("media")
            audio_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            audio_path = audio_dir / f"narration_{timestamp}.mp3"
            await etts.text_to_mp3(narration, str(audio_path))
            await update_progress(session_id, "youtube", 95, "Audio narration file generated")
        except Exception as e:
            audio_path = None
            await update_progress(session_id, "youtube", 95, "Audio generation failed")

        # 5. Finalize: Construct lesson data and mark as complete
        lesson_data = {
            "title": title,
            "courseId": course_id,
            "content": {"root": {"children": lexical_children}},
            "narration": narration,
            "content": {
                "root": {
                    "children": lexical_children,
                    "direction": "ltr",
                    "format": "",
                    "indent": 0,
                    "type": "root",
                    "version": 1
                }
            },
            "published": True,
            "course": {"id": course_id},
        }

        await update_progress(session_id, "selection", 100, "Lesson ready for video selection")
        print("✓ Lesson generation completed successfully")
        
        # Store lesson result for later retrieval instead of cleaning up immediately
        progress_tracker[session_id]["lesson_data"] = lesson_data
        progress_tracker[session_id]["keywords"] = keywords
        progress_tracker[session_id]["youtube_videos"] = youtube_videos
        
        # Note: Don't clean up progress_tracker here - we need it for lesson-result endpoint

    except HTTPException:
        # Re-raise HTTP exceptions (these have user-friendly messages)
        raise
    except Exception as e:
        print(f"✗ Unexpected error during lesson generation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lesson generation failed: {str(e)}")
    finally:
        # Always clean up temp file
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
            print(f"Cleaned up temp file: {temp_path}")

class FinishRequest(BaseModel):
    selected_videos: List[Dict]
    lesson_data: Dict
    auth_token: str

@app.post("/finish/")
async def finish(request: FinishRequest):
    try:
        # Get lexical children from lesson data
        lexical_children = request.lesson_data["content"]["root"]["children"]
        
        # Handle audio upload if there's audio content
        audio_metadata = None
        audio_path = None
        
        # Look for audio content in the lesson data or try to find generated audio
        # For now, we'll create a placeholder since the actual audio handling needs the services
        try:
            # Try to find the most recent audio file in media directory
            media_dir = pathlib.Path("media")
            if media_dir.exists():
                audio_files = list(media_dir.glob("narration_*.mp3"))
                if audio_files:
                    # Get the most recent audio file
                    audio_path = max(audio_files, key=lambda p: p.stat().st_mtime)
                    audio_alt = f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    # Upload to Payload CMS
                    audio_payload = payload.upload_media(str(audio_path), media_type="audio", alt=audio_alt, auth_token=request.auth_token)
                    
                    # Handle different possible response structures
                    media_id = audio_payload.get("id") or audio_payload.get("doc", {}).get("id")
                    audio_metadata = {
                        "type": "upload",
                        "version": 3,
                        "format": "",
                        "id": audio_alt,
                        "fields": None,
                        "relationTo": "media",
                        "value": media_id
                    }
        except Exception as e:
            print(f"Warning: Audio upload failed: {e}")
            # Continue without audio

        # Download and upload each selected video
        video_nodes = []
        for idx, video in enumerate(request.selected_videos):
            try:
                video_url = video["url"]
                # Download video to local media directory
                video_dir = pathlib.Path("media")
                video_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                video_filename = f"video_{idx}_{timestamp}.mp4"
                video_path = video_dir / video_filename
                youtube.download_video(video_url, str(video_path))
                
                # Upload to Payload CMS
                video_alt = f"video_{idx}_{timestamp}"
                payload_result = payload.upload_media(str(video_path), media_type="video", alt=video_alt, auth_token=request.auth_token)
                
                # Handle different possible response structures
                video_media_id = payload_result.get("id") or payload_result.get("doc", {}).get("id")
                # Prepare video metadata node (type 'upload', relationTo 'media')
                video_metadata = {
                    "type": "upload",
                    "version": 3,
                    "format": "",
                    "id": video_alt,  # Use alt as Lexical node ID
                    "fields": None,
                    "relationTo": "media",
                    "value": video_media_id  # Use the media ID directly
                }
                video_nodes.append(video_metadata)
                # Optionally, delete local video file after upload
                video_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"Warning: Video {idx} upload failed: {e}")
                # Continue with other videos

        # Build final lexical children structure
        final_children = []
        
        # Add audio node if we have it
        if audio_metadata:
            final_children.append(audio_metadata)
        
        # Add original content
        final_children.extend(lexical_children)
        
        # Add video nodes
        final_children.extend(video_nodes)
        
        # Update lesson data
        request.lesson_data["content"]["root"]["children"] = final_children

        # Upload the lesson to Payload CMS
        lesson_upload_result = payload.upload_lesson(request.lesson_data, auth_token=request.auth_token)

        return JSONResponse(content={"lesson": request.lesson_data, "payload_result": lesson_upload_result})
        
    except Exception as e:
        print(f"Error in finish endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to finish lesson: {str(e)}")

# Global progress tracking
progress_tracker = {}

@app.post("/cleanup/")
async def cleanup():
    """
    Cleanup endpoint to handle failed or cancelled lesson generation.
    Removes temporary files and performs any necessary cleanup.
    """
    try:
        print("Performing cleanup...")
        cleaned_files = 0
        
        # Clean up media directory (audio and video files)
        media_dir = pathlib.Path("media")
        if media_dir.exists():
            for file_path in media_dir.glob("*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        print(f"Cleaned up media file: {file_path}")
                        cleaned_files += 1
                    except Exception as e:
                        print(f"Failed to clean up {file_path}: {e}")
        
        # Clean up temp directory
        temp_dir = pathlib.Path("temp")
        if temp_dir.exists():
            for file_path in temp_dir.glob("*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        print(f"Cleaned up temp file: {file_path}")
                        cleaned_files += 1
                    except Exception as e:
                        print(f"Failed to clean up {file_path}: {e}")
        
        print(f"Cleanup completed - removed {cleaned_files} files")
        return JSONResponse(content={"status": "cleaned", "message": f"Cleanup completed - removed {cleaned_files} files"})
        
    except Exception as e:
        print(f"Cleanup error: {e}")
        return JSONResponse(content={"status": "error", "message": f"Cleanup failed: {str(e)}"}, status_code=500)

@app.get("/progress/{session_id}")
async def get_progress(session_id: str):
    """
    Get the current progress of a lesson generation session.
    """
    if session_id in progress_tracker:
        return JSONResponse(content=progress_tracker[session_id])
    else:
        return JSONResponse(content={"error": "Session not found"}, status_code=404)

async def update_progress(session_id: str, stage: str, progress: int, message: str):
    """
    Update the progress for a specific session and send WebSocket update.
    """
    progress_data = {
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    progress_tracker[session_id] = progress_data
    print(f"Progress Update [{session_id}]: {stage} - {progress}% - {message}")
    
    # Send WebSocket update if client is connected
    await manager.send_progress_update(session_id, progress_data)

@app.websocket("/ws/lesson-progress/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time lesson generation progress updates.
    """
    await manager.connect(websocket, session_id)
    try:
        # Send current progress if session exists
        if session_id in progress_tracker:
            await manager.send_progress_update(session_id, progress_tracker[session_id])
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(session_id)

@app.post("/cancel-lesson-generation/{session_id}")
async def cancel_lesson_generation(session_id: str):
    """
    Cancel an ongoing lesson generation and clean up resources.
    """
    try:
        # Remove from progress tracker
        if session_id in progress_tracker:
            del progress_tracker[session_id]
        
        # Disconnect WebSocket if connected
        manager.disconnect(session_id)
        
        # Send cancellation update
        cancellation_data = {
            "stage": "cancelled",
            "progress": 0,
            "message": "Lesson generation cancelled by user",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_progress_update(session_id, cancellation_data)
        
        # Trigger cleanup
        await cleanup()
        
        return JSONResponse(content={"status": "cancelled", "message": "Lesson generation cancelled successfully"})
    except Exception as e:
        print(f"Error cancelling lesson generation: {e}")
        return JSONResponse(content={"status": "error", "message": f"Failed to cancel: {str(e)}"}, status_code=500)

@app.get("/foundation-prompt")
async def get_foundation_prompt():
    """
    Get the foundation prompt for display in the UI.
    """
    try:
        foundation_prompt = load_foundation_prompt()
        config_path = pathlib.Path("config/prompts.json")
        config = {}
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        return JSONResponse(content={
            "foundation_prompt": foundation_prompt,
            "description": config.get("description", ""),
            "version": config.get("version", "1.0")
        })
    except Exception as e:
        print(f"Error getting foundation prompt: {e}")
        return JSONResponse(content={"error": f"Failed to get prompt: {str(e)}"}, status_code=500)

@app.post("/search-youtube/")
async def search_youtube(keywords: list = Body(..., embed=True)):
    """
    Search YouTube for videos matching the given keywords.
    Expects: {"keywords": ["keyword1", "keyword2", ...]}
    Returns: List of video metadata (title, videoId, thumbnail, url)
    """
    results = youtube.search_videos(keywords, max_results=10)
    return {"videos": results}

@app.post("/add-youtube-video/")
async def add_youtube_video(link: str = Body(..., embed=True)):
    """
    Accepts a YouTube video link, fetches its metadata, and returns it in the same format as search results.
    Expects: {"link": "https://www.youtube.com/watch?v=VIDEO_ID"}
    """
    # Extract video ID from the link
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", link)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid YouTube link.")
    video_id = match.group(1)

    # Fetch video metadata using YouTube API
    video_data = youtube.search_videos([video_id], max_results=1)
    if not video_data:
        raise HTTPException(status_code=404, detail="Video not found.")

    return {"video": video_data[0]}

@app.post("/process-pdf/")
async def process_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    course_id: str = Form(...),
    auth_token: str = Form(...),
    prompt: str = Form(None)
):
    """
    Upload and process a PDF file to generate a lesson.
    Starts the lesson generation process in the background and returns a session ID.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Create a unique session ID
        session_id = f"lesson_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Save uploaded file temporarily
        temp_dir = pathlib.Path("temp")
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / f"{session_id}_{file.filename}"
        
        # Write the uploaded file
        content = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(content)
        
        print(f"✓ PDF uploaded: {file.filename} -> {temp_path}")
        
        # Initialize progress tracker
        progress_tracker[session_id] = {
            "stage": "upload",
            "progress": 0,
            "message": "PDF uploaded successfully",
            "timestamp": datetime.now().isoformat()
        }
        
        # Combine foundation prompt with user prompt if provided
        foundation_prompt = load_foundation_prompt()
        final_prompt = foundation_prompt
        if prompt and prompt.strip():
            final_prompt = f"{foundation_prompt}\n\nAdditional Instructions:\n{prompt}"
        
        # Start background task for lesson generation
        background_tasks.add_task(
            generate_lesson_task,
            session_id,
            temp_path,
            title,
            int(course_id),
            auth_token,
            final_prompt
        )
        
        return JSONResponse(content={
            "session_id": session_id,
            "message": "PDF processing started",
            "status": "started"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.get("/lesson-result/{session_id}")
async def get_lesson_result(session_id: str):
    """
    Get the final lesson result after generation is complete.
    """
    try:
        # Check if lesson generation is complete
        if session_id not in progress_tracker:
            raise HTTPException(status_code=404, detail="Session not found")
        
        progress_data = progress_tracker[session_id]
        if progress_data["stage"] != "selection" or progress_data["progress"] < 100:
            raise HTTPException(status_code=202, detail="Lesson generation still in progress")
        
        # Get the stored lesson data from the progress tracker
        lesson_data = progress_data.get("lesson_data")
        youtube_videos = progress_data.get("youtube_videos", [])
        
        if not lesson_data:
            raise HTTPException(status_code=500, detail="Lesson data not found")
        
        # Clean up progress tracker now that we've retrieved the data
        del progress_tracker[session_id]
        
        return JSONResponse(content={
            "lesson_data": lesson_data,
            "youtube_videos": youtube_videos,
            "session_id": session_id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting lesson result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get lesson result: {str(e)}")

# ===== CHATBOT API ENDPOINTS =====

class ChatMessage(BaseModel):
    message: str
    lesson_id: int
    conversation_id: Optional[str] = None
    mode: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    related_lessons: List[Dict] = []
    suggestions: List[str] = []
    timestamp: str

@app.post("/api/chat/send")
async def send_chat_message(chat_request: ChatMessage, request: Request):
    """
    Send a message to the chatbot and get a response.
    """
    try:
        # Get auth token from request headers
        auth_header = request.headers.get("authorization")
        auth_token = None
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]
        
        # Create or get existing session
        if chat_request.conversation_id:
            session = chatbot_service.get_session(chat_request.conversation_id)
            if not session:
                # Session expired or invalid, create new one
                session_id = chatbot_service.create_session(chat_request.lesson_id)
            else:
                session_id = chat_request.conversation_id
        else:
            session_id = chatbot_service.create_session(chat_request.lesson_id)
        
        # Generate response with auth token
        result = await chatbot_service.generate_response(
            session_id=session_id,
            message=chat_request.message,
            mode=chat_request.mode,
            auth_token=auth_token
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat message: {str(e)}")

@app.get("/api/chat/context/{lesson_id}")
async def get_chat_context(lesson_id: int, request: Request):
    """
    Get lesson context for chat initialization.
    """
    try:
        # Get auth token from request headers
        auth_header = request.headers.get("authorization")
        auth_token = None
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]
        
        context = await chatbot_service.get_lesson_context(lesson_id, auth_token)
        
        if not context:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        return JSONResponse(content={
            "lesson": {
                "id": lesson_id,
                "title": context.get("lesson", {}).get("title", ""),
                "course": context.get("course", {})
            },
            "keywords": context.get("keywords", []),
            "context_summary": context.get("context_summary", "")
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting chat context: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat context: {str(e)}")

@app.get("/api/chat/related-lessons/{lesson_id}")
async def get_related_lessons(lesson_id: int, request: Request, limit: int = 5):
    """
    Find lessons related to the current one.
    """
    try:
        # Get auth token from request headers
        auth_header = request.headers.get("authorization")
        auth_token = None
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]
        
        # Get lesson context first to extract keywords
        context = await chatbot_service.get_lesson_context(lesson_id, auth_token)
        keywords = context.get("keywords", [])
        
        if not keywords:
            return JSONResponse(content={"related_lessons": []})
        
        related_lessons = await chatbot_service.find_related_lessons(lesson_id, keywords, limit, auth_token)
        
        return JSONResponse(content={"related_lessons": related_lessons})
        
    except Exception as e:
        print(f"Error finding related lessons: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to find related lessons: {str(e)}")

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time chat communication.
    Note: Auth token should be passed as query parameter since WebSocket headers are limited.
    """
    await websocket.accept()
    print(f"Chat WebSocket connected for session: {session_id}")
    
    # Store the auth token for this WebSocket session
    auth_token = token
    if not auth_token:
        print(f"Warning: No auth token provided for WebSocket session {session_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                content = data.get("content")
                lesson_id = data.get("lesson_id")
                mode = data.get("mode", "default")
                
                if not content or not lesson_id:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Missing message content or lesson_id"
                    })
                    continue
                
                # Get or create session
                session = chatbot_service.get_session(session_id)
                if not session:
                    session_id = chatbot_service.create_session(lesson_id)
                
                try:
                    # Send typing indicator
                    await websocket.send_json({
                        "type": "typing",
                        "content": "AI is thinking...",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Check if LLM supports streaming
                    if hasattr(llm_service, 'generate_streaming_response'):
                        # Get context for streaming
                        session = chatbot_service.get_session(session_id)
                        if not session.context_cache:
                            session.context_cache = await chatbot_service.get_lesson_context(lesson_id, auth_token)
                        
                        context = session.context_cache
                        lesson_content = context.get("context_summary", "")
                        
                        # Add user message to history
                        session.add_message("user", content)
                        
                        # Build context for LLM
                        prompts = chatbot_service.load_system_prompts()
                        system_prompt = prompts.get(mode, prompts["default"])
                        
                        llm_context = f"Lesson Content: {lesson_content}\n\n"
                        recent_history = session.get_recent_history(5)
                        if recent_history:
                            llm_context += "Recent conversation:\n"
                            for msg in recent_history[:-1]:
                                llm_context += f"{msg['role'].title()}: {msg['content']}\n"
                            llm_context += "\n"
                        
                        # Stream response
                        full_response = ""
                        async for token in llm_service.generate_streaming_response(
                            prompt=content,
                            system_prompt=system_prompt,
                            context=llm_context
                        ):
                            full_response += token
                            await websocket.send_json({
                                "type": "token",
                                "content": token,
                                "partial": True,
                                "timestamp": datetime.now().isoformat()
                            })
                        
                        # Add complete response to history
                        session.add_message("assistant", full_response)
                        
                        # Send completion signal with suggestions
                        keywords = context.get("keywords", [])
                        related_lessons = await chatbot_service.find_related_lessons(lesson_id, keywords, 3, auth_token)
                        suggestions = chatbot_service.generate_suggestions(content, full_response, mode)
                        
                        await websocket.send_json({
                            "type": "complete",
                            "content": full_response,
                            "related_lessons": related_lessons,
                            "suggestions": suggestions,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                    else:
                        # Fallback to regular response generation
                        result = await chatbot_service.generate_response(
                            session_id=session_id,
                            message=content,
                            mode=mode,
                            auth_token=auth_token  # Use the token provided via query parameter
                        )
                        
                        await websocket.send_json({
                            "type": "response",
                            "content": result["response"],
                            "related_lessons": result.get("related_lessons", []),
                            "suggestions": result.get("suggestions", []),
                            "timestamp": result["timestamp"]
                        })
                
                except Exception as e:
                    print(f"❌ Error processing chat message: {e}")
                    import traceback
                    traceback.print_exc()
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Sorry, I encountered an error: {str(e)}. Please try again.",
                        "timestamp": datetime.now().isoformat()
                    })
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                
    except WebSocketDisconnect:
        print(f"Chat WebSocket disconnected for session: {session_id}")
    except Exception as e:
        print(f"Chat WebSocket error for session {session_id}: {e}")
    finally:
        print(f"Chat WebSocket closed for session: {session_id}")

@app.get("/api/chat/health")
async def chat_health_check():
    """
    Health check endpoint for chat functionality.
    """
    try:
        llm_available = await llm_service.is_available()
        
        return JSONResponse(content={
            "status": "healthy" if llm_available else "degraded",
            "llm_available": llm_available,
            "timestamp": datetime.now().isoformat(),
            "active_sessions": len(chatbot_service.sessions)
        })
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

@app.post("/api/chat/cleanup")
async def cleanup_chat_sessions():
    """
    Cleanup old chat sessions.
    """
    try:
        initial_count = len(chatbot_service.sessions)
        chatbot_service.cleanup_old_sessions(max_age_hours=24)
        final_count = len(chatbot_service.sessions)
        cleaned = initial_count - final_count
        
        return JSONResponse(content={
            "message": f"Cleaned up {cleaned} expired chat sessions",
            "active_sessions": final_count
        })
        
    except Exception as e:
        print(f"Error cleaning up chat sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("ENVIRONMENT", "production") == "development"
    uvicorn.run("api:app", host=host, port=port, reload=reload)
