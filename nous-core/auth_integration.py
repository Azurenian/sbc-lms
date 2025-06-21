"""PI-AI Authentication Integration

This module integrates pi-ai with the pi-frontend authentication system,
allowing pi-ai to use PayloadCMS auth tokens for API requests.
"""

import sys
import os
from pathlib import Path

# Add pi-frontend to path
frontend_path = Path(__file__).parent.parent / "pi-frontend"
sys.path.insert(0, str(frontend_path))

try:
    from services.auth_service import (
        get_auth_token,
        authenticate,
        get_current_user,
        is_authenticated,
        logout
    )
except ImportError as e:
    print(f"Error importing auth service: {e}")
    print("Make sure pi-frontend is set up correctly.")
    sys.exit(1)

import asyncio
import httpx
from typing import Optional, Dict, Any

class PIAIAuthIntegration:
    """Authentication integration for PI-AI"""
    
    def __init__(self, payload_url: str = "http://localhost:3000"):
        self.payload_url = payload_url
    
    async def ensure_authenticated(self, email: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Ensure pi-ai is authenticated, login if necessary"""
        # Check if already authenticated
        if await is_authenticated():
            print("✅ Already authenticated")
            return True
        
        # Try to authenticate if credentials provided
        if email and password:
            print(f"🔐 Authenticating as {email}...")
            result = await authenticate(email, password)
            if result["success"]:
                print(f"✅ Authentication successful: {result['user']['email']}")
                return True
            else:
                print(f"❌ Authentication failed: {result['error']}")
                return False
        
        print("❌ Not authenticated and no credentials provided")
        return False
    
    async def get_authenticated_headers(self) -> Optional[Dict[str, str]]:
        """Get headers with authentication token for API requests"""
        token = await get_auth_token()
        if token:
            return {
                "Authorization": f"JWT {token}",
                "Content-Type": "application/json"
            }
        return None
    
    async def make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to PayloadCMS API"""
        headers = await self.get_authenticated_headers()
        if not headers:
            return {"success": False, "error": "Not authenticated"}
        
        # Merge with any existing headers
        if "headers" in kwargs:
            kwargs["headers"].update(headers)
        else:
            kwargs["headers"] = headers
        
        url = f"{self.payload_url}/api{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, **kwargs)
                
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {
                        "success": False, 
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
            except Exception as e:
                return {"success": False, "error": f"Request failed: {str(e)}"}
    
    async def get_user_courses(self) -> Dict[str, Any]:
        """Get courses for the current user"""
        return await self.make_authenticated_request("GET", "/courses")
    
    async def get_user_enrollments(self) -> Dict[str, Any]:
        """Get enrollments for the current user"""
        return await self.make_authenticated_request("GET", "/enrollments")
    
    async def get_course_lessons(self, course_id: str) -> Dict[str, Any]:
        """Get lessons for a specific course"""
        return await self.make_authenticated_request("GET", f"/lessons?where[course][equals]={course_id}")
    
    async def create_lesson(self, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lesson (for instructors/admins)"""
        return await self.make_authenticated_request("POST", "/lessons", json=lesson_data)
    
    async def get_current_user_info(self) -> Dict[str, Any]:
        """Get current user information"""
        result = await get_current_user()
        if result["success"]:
            user = result["user"]
            return {
                "success": True,
                "user": {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "firstName": user.get("firstName"),
                    "lastName": user.get("lastName"),
                    "role": user.get("role"),
                    "fullName": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                }
            }
        return result
    
    def logout_user(self) -> None:
        """Logout the current user"""
        logout()
        print("🔓 Logged out successfully")


# Convenience functions for easy import
_auth_integration = None

def get_auth_integration() -> PIAIAuthIntegration:
    """Get global auth integration instance"""
    global _auth_integration
    if _auth_integration is None:
        _auth_integration = PIAIAuthIntegration()
    return _auth_integration

async def ensure_pi_ai_authenticated(email: Optional[str] = None, password: Optional[str] = None) -> bool:
    """Ensure pi-ai is authenticated"""
    integration = get_auth_integration()
    return await integration.ensure_authenticated(email, password)

async def get_pi_ai_headers() -> Optional[Dict[str, str]]:
    """Get authentication headers for pi-ai requests"""
    integration = get_auth_integration()
    return await integration.get_authenticated_headers()

async def pi_ai_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make authenticated request from pi-ai"""
    integration = get_auth_integration()
    return await integration.make_authenticated_request(method, endpoint, **kwargs)


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        print("🤖 PI-AI Authentication Integration Test")
        print("=" * 50)
        
        integration = PIAIAuthIntegration()
        
        # Test authentication (replace with actual credentials)
        email = input("Enter email (or press Enter to skip): ").strip()
        if email:
            password = input("Enter password: ").strip()
            
            if await integration.ensure_authenticated(email, password):
                print("\n📋 Getting user info...")
                user_info = await integration.get_current_user_info()
                if user_info["success"]:
                    user = user_info["user"]
                    print(f"👤 User: {user['fullName']} ({user['email']})")
                    print(f"🎭 Role: {user['role']}")
                
                print("\n📚 Getting courses...")
                courses = await integration.get_user_courses()
                if courses["success"]:
                    course_data = courses["data"]
                    print(f"📖 Found {len(course_data.get('docs', []))} courses")
                else:
                    print(f"❌ Failed to get courses: {courses['error']}")
                
                print("\n📝 Getting enrollments...")
                enrollments = await integration.get_user_enrollments()
                if enrollments["success"]:
                    enrollment_data = enrollments["data"]
                    print(f"🎓 Found {len(enrollment_data.get('docs', []))} enrollments")
                else:
                    print(f"❌ Failed to get enrollments: {enrollments['error']}")
                
                # Test logout
                integration.logout_user()
            else:
                print("❌ Authentication failed")
        else:
            print("⏭️ Skipping authentication test")
        
        print("\n✅ Test completed")
    
    asyncio.run(main())
