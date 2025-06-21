"""Shared Authentication Service for PI-AI Integration

This module provides authentication functionality that can be used by both
the frontend application and the pi-ai service to manage PayloadCMS auth tokens.
"""

import httpx
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

class PIAuthService:
    """Shared authentication service for PI-LMS ecosystem"""
    
    def __init__(self, payload_url: str = "http://localhost:3000"):
        self.payload_url = payload_url
        self.token_file = Path("auth_token.json")
        self._current_token = None
        self._token_expires_at = None
        
    def _save_token(self, token_data: Dict[str, Any]) -> None:
        """Save token data to file for persistence"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
        except Exception as e:
            print(f"Warning: Could not save token to file: {e}")
    
    def _load_token(self) -> Optional[Dict[str, Any]]:
        """Load token data from file"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load token from file: {e}")
        return None
    
    def _is_token_valid(self, token_data: Dict[str, Any]) -> bool:
        """Check if stored token is still valid"""
        if not token_data or 'expires_at' not in token_data:
            return False
        
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        return datetime.now() < expires_at - timedelta(minutes=5)  # 5 min buffer
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate with PayloadCMS and store token"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.payload_url}/api/users/login",
                    json={"email": email, "password": password},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("token")
                    user = data.get("user")
                    exp = data.get("exp")
                    
                    if token:
                        # Calculate expiration time
                        expires_at = datetime.now() + timedelta(hours=24)
                        if exp:
                            expires_at = datetime.fromtimestamp(exp)
                        
                        token_data = {
                            "token": token,
                            "user": user,
                            "expires_at": expires_at.isoformat()
                        }
                        
                        self._save_token(token_data)
                        self._current_token = token
                        self._token_expires_at = expires_at
                        
                        return {
                            "success": True,
                            "token": token,
                            "user": user,
                            "expires_at": expires_at.isoformat()
                        }
                    else:
                        return {"success": False, "error": "No token received"}
                else:
                    return {"success": False, "error": "Invalid credentials"}
                    
            except Exception as e:
                return {"success": False, "error": f"Connection error: {str(e)}"}
    
    async def get_valid_token(self) -> Optional[str]:
        """Get a valid authentication token"""
        # Check current token in memory
        if (self._current_token and self._token_expires_at and 
            datetime.now() < self._token_expires_at - timedelta(minutes=5)):
            return self._current_token
        
        # Try to load token from file
        token_data = self._load_token()
        if token_data and self._is_token_valid(token_data):
            self._current_token = token_data["token"]
            self._token_expires_at = datetime.fromisoformat(token_data["expires_at"])
            return self._current_token
        
        return None
    
    async def get_user_info(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Get current user information"""
        if not token:
            token = await self.get_valid_token()
        
        if not token:
            return {"success": False, "error": "No valid token available"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.payload_url}/api/users/me",
                    headers={"Authorization": f"JWT {token}"}
                )
                
                if response.status_code == 200:
                    return {"success": True, "user": response.json().get("user")}
                else:
                    return {"success": False, "error": "Invalid token"}
                    
            except Exception as e:
                return {"success": False, "error": f"Connection error: {str(e)}"}
    
    async def refresh_token(self) -> Dict[str, Any]:
        """Refresh the current token"""
        token = await self.get_valid_token()
        if not token:
            return {"success": False, "error": "No token to refresh"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.payload_url}/api/users/refresh-token",
                    headers={"Authorization": f"JWT {token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    new_token = data.get("token")
                    if new_token:
                        expires_at = datetime.now() + timedelta(hours=24)
                        token_data = {
                            "token": new_token,
                            "user": data.get("user"),
                            "expires_at": expires_at.isoformat()
                        }
                        
                        self._save_token(token_data)
                        self._current_token = new_token
                        self._token_expires_at = expires_at
                        
                        return {"success": True, "token": new_token}
                
                return {"success": False, "error": "Could not refresh token"}
                
            except Exception as e:
                return {"success": False, "error": f"Connection error: {str(e)}"}
    
    def logout(self) -> None:
        """Clear stored authentication data"""
        self._current_token = None
        self._token_expires_at = None
        
        try:
            if self.token_file.exists():
                self.token_file.unlink()
        except Exception as e:
            print(f"Warning: Could not delete token file: {e}")
    
    async def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        token = await self.get_valid_token()
        if not token:
            return False
        
        # Verify token with server
        user_info = await self.get_user_info(token)
        return user_info.get("success", False)


# Convenience functions for pi-ai integration
_auth_service = None

def get_auth_service() -> PIAuthService:
    """Get global auth service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = PIAuthService()
    return _auth_service

async def get_auth_token() -> Optional[str]:
    """Get current auth token (for pi-ai)"""
    auth_service = get_auth_service()
    return await auth_service.get_valid_token()

async def authenticate(email: str, password: str) -> Dict[str, Any]:
    """Authenticate user (for pi-ai)"""
    auth_service = get_auth_service()
    return await auth_service.login(email, password)

async def get_current_user() -> Dict[str, Any]:
    """Get current user info (for pi-ai)"""
    auth_service = get_auth_service()
    return await auth_service.get_user_info()

async def is_authenticated() -> bool:
    """Check if authenticated (for pi-ai)"""
    auth_service = get_auth_service()
    return await auth_service.is_authenticated()

def logout():
    """Logout user (for pi-ai)"""
    auth_service = get_auth_service()
    auth_service.logout()


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        auth = PIAuthService()
        
        # Example login
        result = await auth.login("admin@example.com", "password")
        if result["success"]:
            print(f"Login successful: {result['user']['email']}")
            
            # Get user info
            user_info = await auth.get_user_info()
            print(f"User info: {user_info}")
            
            # Check authentication
            is_auth = await auth.is_authenticated()
            print(f"Is authenticated: {is_auth}")
            
            # Logout
            auth.logout()
            print("Logged out")
        else:
            print(f"Login failed: {result['error']}")
    
    asyncio.run(main())
