from fastapi import FastAPI, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import json
from typing import Optional
import os
from datetime import datetime, timedelta

app = FastAPI(title="PI-LMS Frontend", description="Frontend interface for PI-LMS")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Security
security = HTTPBearer(auto_error=False)

# Configuration
PAYLOAD_CMS_URL = os.getenv("PAYLOAD_CMS_URL", "http://localhost:3000")  # PayloadCMS backend URL
SESSION_SECRET = "your-secret-key-here"  # In production, use environment variable

# In-memory session storage (in production, use Redis or database)
sessions = {}

class AuthService:
    """Authentication service for PayloadCMS integration"""
    
    @staticmethod
    async def login(email: str, password: str) -> dict:
        """Authenticate user with PayloadCMS"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{PAYLOAD_CMS_URL}/api/users/login",
                    json={"email": email, "password": password},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "token": data.get("token"),
                        "user": data.get("user"),
                        "expires": data.get("exp")
                    }
                else:
                    return {"success": False, "error": "Invalid credentials"}
                    
            except Exception as e:
                return {"success": False, "error": f"Connection error: {str(e)}"}
    
    @staticmethod
    async def get_user_info(token: str) -> dict:
        """Get current user information"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{PAYLOAD_CMS_URL}/api/users/me",
                    headers={"Authorization": f"JWT {token}"}
                )
                
                if response.status_code == 200:
                    return {"success": True, "user": response.json().get("user")}
                else:
                    return {"success": False, "error": "Invalid token"}
                    
            except Exception as e:
                return {"success": False, "error": f"Connection error: {str(e)}"}
    
    @staticmethod
    def create_session(user_data: dict, token: str) -> str:
        """Create a new session"""
        session_id = f"session_{datetime.now().timestamp()}"
        sessions[session_id] = {
            "user": user_data,
            "token": token,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }
        return session_id
    
    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """Get session data"""
        session = sessions.get(session_id)
        if session and session["expires_at"] > datetime.now():
            return session
        elif session:
            # Remove expired session
            del sessions[session_id]
        return None
    
    @staticmethod
    def delete_session(session_id: str):
        """Delete session"""
        if session_id in sessions:
            del sessions[session_id]

def get_current_session(request: Request) -> Optional[dict]:
    """Get current user session from cookies"""
    session_id = request.cookies.get("session_id")
    if session_id:
        return AuthService.get_session(session_id)
    return None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirect to login or dashboard based on auth status"""
    session = get_current_session(request)
    if session:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    session = get_current_session(request)
    if session:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/login")
async def api_login(request: Request, email: str = Form(...), password: str = Form(...)):
    """API endpoint for login"""
    auth_result = await AuthService.login(email, password)
    
    if auth_result["success"]:
        session_id = AuthService.create_session(auth_result["user"], auth_result["token"])
        response = JSONResponse({"success": True, "redirect": "/dashboard"})
        response.set_cookie(
            key="session_id", 
            value=session_id, 
            httponly=True, 
            max_age=86400,  # 24 hours
            samesite="lax"
        )
        return response
    else:
        return JSONResponse(
            {"success": False, "error": auth_result["error"]}, 
            status_code=400
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page"""
    session = get_current_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": session["user"]
    })

@app.get("/lesson-generator", response_class=HTMLResponse)
async def lesson_generator(request: Request):
    """AI Lesson Generator page - Admin and Instructor only"""
    session = get_current_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    
    # Check if user has permission to access lesson generator
    user_role = session["user"].get("role")
    if user_role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Access denied. Admin or Instructor role required.")
    
    return templates.TemplateResponse("lesson_generator.html", {
        "request": request,
        "user": session["user"]
    })

@app.post("/api/logout")
async def api_logout(request: Request):
    """API endpoint for logout"""
    session_id = request.cookies.get("session_id")
    if session_id:
        AuthService.delete_session(session_id)
    
    response = JSONResponse({"success": True, "redirect": "/login"})
    response.delete_cookie("session_id")
    return response

@app.get("/api/me")
async def api_me(request: Request):
    """Get current user info - for pi-ai integration"""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {"user": session["user"], "token": session["token"]}

@app.get("/api/token")
async def api_get_token(request: Request):
    """Get auth token - for pi-ai integration"""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {"token": session["token"]}

@app.get("/courses", response_class=HTMLResponse)
async def courses_page(request: Request):
    """Courses listing page"""
    session = get_current_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("courses.html", {
        "request": request,
        "user": session["user"]
    })

@app.get("/courses/{course_id}", response_class=HTMLResponse)
async def course_detail_page(request: Request, course_id: int):
    """Course detail page showing lessons"""
    session = get_current_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYLOAD_CMS_URL}/api/courses/{course_id}",
                headers={"Authorization": f"JWT {session['token']}"}
            )
            
            if response.status_code == 200:
                course_data = response.json()
                return templates.TemplateResponse("course_detail.html", {
                    "request": request,
                    "user": session["user"],
                    "course": course_data
                })
            else:
                raise HTTPException(status_code=404, detail="Course not found")
                
    except Exception as e:
        print(f"Error fetching course: {e}")
        raise HTTPException(status_code=500, detail="Failed to load course")

@app.get("/lessons/{lesson_id}", response_class=HTMLResponse)
async def lesson_view_page(request: Request, lesson_id: int):
    """Lesson view page"""
    session = get_current_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYLOAD_CMS_URL}/api/lessons/{lesson_id}",
                headers={"Authorization": f"JWT {session['token']}"}
            )
            
            if response.status_code == 200:
                lesson_data = response.json()
                
                # Check if student is trying to access unpublished lesson
                user_role = session["user"].get("role")
                if user_role == "student" and not lesson_data.get("published", False):
                    raise HTTPException(status_code=404, detail="Lesson not found")
                
                return templates.TemplateResponse("lesson_view.html", {
                    "request": request,
                    "user": session["user"],
                    "lesson": lesson_data
                })
            else:
                raise HTTPException(status_code=404, detail="Lesson not found")
                
    except Exception as e:
        print(f"Error fetching lesson: {e}")
        raise HTTPException(status_code=500, detail="Failed to load lesson")

@app.get("/lessons/{lesson_id}/edit", response_class=HTMLResponse)
async def lesson_edit_page(request: Request, lesson_id: int):
    """Lesson edit page - Admin and Instructor only"""
    session = get_current_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    
    # Check if user has permission to edit lessons
    user_role = session["user"].get("role")
    if user_role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Access denied. Admin or Instructor role required.")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYLOAD_CMS_URL}/api/lessons/{lesson_id}",
                headers={"Authorization": f"JWT {session['token']}"}
            )
            
            if response.status_code == 200:
                lesson_data = response.json()
                return templates.TemplateResponse("lesson_edit.html", {
                    "request": request,
                    "user": session["user"],
                    "lesson": lesson_data
                })
            else:
                raise HTTPException(status_code=404, detail="Lesson not found")
                
    except Exception as e:
        print(f"Error fetching lesson: {e}")
        raise HTTPException(status_code=500, detail="Failed to load lesson")

@app.get("/api/courses")
async def api_get_courses(request: Request):
    """Get available courses from PayloadCMS"""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_role = session["user"].get("role")
        user_id = session["user"].get("id")
        
        async with httpx.AsyncClient() as client:
            # For students, get only enrolled courses
            if user_role == "student":
                # First get enrollments for this student
                enrollments_response = await client.get(
                    f"{PAYLOAD_CMS_URL}/api/enrollments?where[user][equals]={user_id}",
                    headers={"Authorization": f"JWT {session['token']}"}
                )
                
                if enrollments_response.status_code == 200:
                    enrollments_data = enrollments_response.json()
                    course_ids = [enrollment["course"]["id"] for enrollment in enrollments_data.get("docs", []) if enrollment.get("course")]
                    
                    if course_ids:
                        # Get courses by IDs
                        courses_query = "&".join([f"where[id][in][]={course_id}" for course_id in course_ids])
                        response = await client.get(
                            f"{PAYLOAD_CMS_URL}/api/courses?{courses_query}",
                            headers={"Authorization": f"JWT {session['token']}"}
                        )
                    else:
                        return {"courses": []}
                else:
                    return {"courses": [], "error": "Failed to fetch enrollments"}
            
            # For teachers, get only assigned courses
            elif user_role == "instructor":
                response = await client.get(
                    f"{PAYLOAD_CMS_URL}/api/courses?where[instructor][equals]={user_id}",
                    headers={"Authorization": f"JWT {session['token']}"}
                )
            
            # For admins, get all courses
            else:
                response = await client.get(
                    f"{PAYLOAD_CMS_URL}/api/courses",
                    headers={"Authorization": f"JWT {session['token']}"}
                )
            
            if response.status_code == 200:
                courses_data = response.json()
                return {"courses": courses_data.get("docs", [])}
            else:
                return {"courses": [], "error": "Failed to fetch courses"}
                
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return {"courses": [], "error": f"Connection error: {str(e)}"}

@app.get("/api/courses/{course_id}/lessons")
async def api_get_course_lessons(request: Request, course_id: int):
    """Get lessons for a specific course"""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_role = session["user"].get("role")
        
        async with httpx.AsyncClient() as client:
            # For students, only show published lessons
            if user_role == "student":
                response = await client.get(
                    f"{PAYLOAD_CMS_URL}/api/lessons?where[course][equals]={course_id}&where[published][equals]=true&sort=createdAt",
                    headers={"Authorization": f"JWT {session['token']}"}
                )
            else:
                # For instructors and admins, show all lessons
                response = await client.get(
                    f"{PAYLOAD_CMS_URL}/api/lessons?where[course][equals]={course_id}&sort=createdAt",
                    headers={"Authorization": f"JWT {session['token']}"}
                )
            
            if response.status_code == 200:
                lessons_data = response.json()
                return {"lessons": lessons_data.get("docs", [])}
            else:
                return {"lessons": [], "error": "Failed to fetch lessons"}
                
    except Exception as e:
        print(f"Error fetching lessons: {e}")
        return {"lessons": [], "error": f"Connection error: {str(e)}"}

@app.get("/api/lessons/{lesson_id}")
async def api_get_lesson(request: Request, lesson_id: int):
    """Get a specific lesson"""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYLOAD_CMS_URL}/api/lessons/{lesson_id}",
                headers={"Authorization": f"JWT {session['token']}"}
            )
            
            if response.status_code == 200:
                lesson_data = response.json()
                
                # Check if student is trying to access unpublished lesson
                user_role = session["user"].get("role")
                if user_role == "student" and not lesson_data.get("published", False):
                    raise HTTPException(status_code=404, detail="Lesson not found")
                
                return {"lesson": lesson_data}
            else:
                raise HTTPException(status_code=404, detail="Lesson not found")
                
    except Exception as e:
        print(f"Error fetching lesson: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch lesson")

@app.put("/api/lessons/{lesson_id}")
async def api_update_lesson(request: Request, lesson_id: int):
    """Update a lesson - Admin and Instructor only"""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if user has permission to edit lessons
    user_role = session["user"].get("role")
    if user_role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Access denied. Admin or Instructor role required.")
    
    try:
        lesson_data = await request.json()
        
        # Comprehensive server-side logging
        print("=== BACKEND LESSON UPDATE DEBUG ===")
        print(f"Lesson ID: {lesson_id}")
        print(f"User: {session['user'].get('email')} ({user_role})")
        print(f"Data received from frontend:")
        print(json.dumps(lesson_data, indent=2))
        
        # Check content structure if present
        if 'content' in lesson_data and lesson_data['content']:
            content = lesson_data['content']
            print(f"Content structure analysis:")
            print(f"- Has root: {'root' in content}")
            if 'root' in content:
                print(f"- Root type: {content['root'].get('type', 'MISSING')}")
                print(f"- Root children count: {len(content['root'].get('children', []))}")
                print(f"- Root children types: {[child.get('type', 'UNKNOWN') for child in content['root'].get('children', [])]}")
        print("=== END BACKEND DEBUG ===")
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{PAYLOAD_CMS_URL}/api/lessons/{lesson_id}",
                json=lesson_data,
                headers={"Authorization": f"JWT {session['token']}"}
            )
            
            print(f"PayloadCMS response status: {response.status_code}")
            
            if response.status_code == 200:
                updated_lesson = response.json()
                print("PayloadCMS update successful!")
                return {"lesson": updated_lesson}
            else:
                error_text = response.text
                print(f"PayloadCMS error response: {error_text}")
                
                try:
                    error_data = response.json()
                    print(f"Parsed PayloadCMS error: {json.dumps(error_data, indent=2)}")
                except:
                    error_data = {"message": error_text}
                
                return JSONResponse(
                    {"error": error_data.get("message", "Failed to update lesson")},
                    status_code=response.status_code
                )
                
    except Exception as e:
        print(f"Error updating lesson: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Connection error: {str(e)}"}, status_code=500)

@app.delete("/api/lessons/{lesson_id}")
async def api_delete_lesson(request: Request, lesson_id: int):
    """Delete a lesson - Admin and Instructor only"""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if user has permission to delete lessons
    user_role = session["user"].get("role")
    if user_role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Access denied. Admin or Instructor role required.")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{PAYLOAD_CMS_URL}/api/lessons/{lesson_id}",
                headers={"Authorization": f"JWT {session['token']}"}
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Lesson deleted successfully"}
            else:
                error_data = response.json() if response.headers.get("content-type") == "application/json" else {}
                return JSONResponse(
                    {"error": error_data.get("message", "Failed to delete lesson")},
                    status_code=response.status_code
                )
                
    except Exception as e:
        print(f"Error deleting lesson: {e}")
        return JSONResponse({"error": f"Connection error: {str(e)}"}, status_code=500)

@app.delete("/api/courses/{course_id}")
async def api_delete_course(request: Request, course_id: int):
    """Delete a course - Admin only"""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if user has permission to delete courses
    user_role = session["user"].get("role")
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin role required.")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{PAYLOAD_CMS_URL}/api/courses/{course_id}",
                headers={"Authorization": f"JWT {session['token']}"}
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Course deleted successfully"}
            else:
                error_data = response.json() if response.headers.get("content-type") == "application/json" else {}
                return JSONResponse(
                    {"error": error_data.get("message", "Failed to delete course")},
                    status_code=response.status_code
                )
                
    except Exception as e:
        print(f"Error deleting course: {e}")
        return JSONResponse({"error": f"Connection error: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
