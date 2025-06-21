#!/usr/bin/env python3
"""Startup script for PI-LMS Frontend

This script provides an easy way to start the PI-LMS frontend server
with proper configuration and error handling.
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import jinja2
        import httpx
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

async def check_backend_connection():
    """Check if PayloadCMS backend is accessible"""
    backend_url = "http://localhost:3000"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{backend_url}/api/users", timeout=5.0)
            if response.status_code in [200, 401]:  # 401 is expected without auth
                print(f"✅ PayloadCMS backend is accessible at {backend_url}")
                return True
            else:
                print(f"⚠️  PayloadCMS backend returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to PayloadCMS backend at {backend_url}")
        print(f"   Error: {e}")
        print("   Make sure the backend is running with: npm run dev")
        return False

def create_env_file():
    """Create a .env file with default configuration if it doesn't exist"""
    env_file = Path(".env")
    if not env_file.exists():
        env_content = """# PI-LMS Frontend Configuration
PAYLOAD_CMS_URL=http://localhost:3000
SESSION_SECRET=your-secret-key-change-in-production
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=8080
DEBUG=true
"""
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"✅ Created {env_file} with default configuration")
    else:
        print(f"✅ Using existing {env_file}")

def load_env():
    """Load environment variables from .env file"""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

async def main():
    """Main startup function"""
    print("🚀 Starting PI-LMS Frontend Server")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create and load environment
    create_env_file()
    load_env()
    
    # Check backend connection
    backend_ok = await check_backend_connection()
    if not backend_ok:
        print("\n⚠️  Backend not accessible, but frontend will still start")
        print("   Some features may not work until backend is available")
    
    print("\n🌐 Starting FastAPI server...")
    print(f"   Frontend URL: http://localhost:{os.getenv('FRONTEND_PORT', '8080')}")
    print(f"   Backend URL: {os.getenv('PAYLOAD_CMS_URL', 'http://localhost:3000')}")
    print("\n📋 Available endpoints:")
    print("   GET  /          - Root (redirects to login/dashboard)")
    print("   GET  /login     - Login page")
    print("   POST /api/login - Login API")
    print("   GET  /dashboard - Dashboard (requires auth)")
    print("   POST /api/logout- Logout API")
    print("   GET  /api/me    - Current user info (for pi-ai)")
    print("   GET  /api/token - Auth token (for pi-ai)")
    print("\n💡 Tips:")
    print("   - Use Ctrl+C to stop the server")
    print("   - The server will auto-reload on code changes")
    print("   - Check browser console for any JavaScript errors")
    print("   - Login credentials are managed through PayloadCMS admin")
    
    try:
        import uvicorn
        from main import app
        
        # Start the server
        config = uvicorn.Config(
            app=app,
            host=os.getenv('FRONTEND_HOST', '0.0.0.0'),
            port=int(os.getenv('FRONTEND_PORT', '8080')),
            reload=os.getenv('DEBUG', 'true').lower() == 'true',
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Please run this script from the pi-frontend directory")
        print("   cd pi-frontend && python start.py")
        sys.exit(1)
    
    # Run the startup
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
