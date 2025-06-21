# PI-LMS Frontend

A modern frontend interface for PI-AI and PI-LMS Backend using FastAPI, HTMX, Alpine.js, and custom CSS.

## Features

- 🔐 **Authentication**: Secure login using PayloadCMS auth tokens
- 🎨 **Modern UI**: Clean, responsive design with custom CSS
- ⚡ **HTMX Integration**: Dynamic interactions without page reloads
- 🏔️ **Alpine.js**: Lightweight JavaScript framework for interactivity
- 📱 **Responsive**: Works on desktop, tablet, and mobile devices
- 🔌 **Offline Ready**: HTMX and Alpine.js downloaded for offline use
- 🤖 **PI-AI Integration**: Shared authentication service for AI components

## Project Structure

```
pi-frontend/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── services/              # Shared services
│   ├── __init__.py
│   └── auth_service.py    # Authentication service for pi-ai integration
├── static/                # Static assets
│   ├── css/
│   │   └── style.css      # Custom CSS styles
│   └── js/
│       ├── htmx.min.js    # HTMX library
│       └── alpine.min.js  # Alpine.js library
└── templates/             # HTML templates
    ├── base.html          # Base template
    ├── login.html         # Login page
    └── dashboard.html     # Dashboard page
```

## Installation

1. **Install Python dependencies:**
   ```bash
   cd pi-frontend
   pip install -r requirements.txt
   ```

2. **Ensure PayloadCMS backend is running:**
   ```bash
   cd ../pi-lms-backend
   npm run dev
   ```
   The backend should be accessible at `http://localhost:3000`

3. **Start the frontend server:**
   ```bash
   python main.py
   ```
   Or use uvicorn directly:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080 --reload
   ```

## Usage

### Accessing the Frontend

1. Open your browser and navigate to `http://localhost:8080`
2. You'll be redirected to the login page
3. Enter your PayloadCMS credentials (email and password)
4. Upon successful login, you'll be redirected to the dashboard

### Default Test User

If you have a fresh PayloadCMS installation, you can create a user through the admin panel at `http://localhost:3000/admin`

### Dashboard Features

- **User Information**: Displays user details and role
- **Quick Actions**: Role-based action buttons
- **System Status**: Shows connection status to backend services
- **Recent Activity**: Shows login and activity history

## PI-AI Integration

The frontend provides a shared authentication service that can be imported and used by pi-ai:

```python
# In pi-ai code
from pi_frontend.services import get_auth_token, authenticate, get_current_user

# Authenticate
result = await authenticate("user@example.com", "password")
if result["success"]:
    print(f"Logged in as: {result['user']['email']}")

# Get current auth token
token = await get_auth_token()
if token:
    # Use token for API requests to PayloadCMS
    headers = {"Authorization": f"JWT {token}"}

# Get current user info
user_info = await get_current_user()
if user_info["success"]:
    print(f"Current user: {user_info['user']}")
```

## API Endpoints

- `GET /` - Root (redirects to login or dashboard)
- `GET /login` - Login page
- `POST /api/login` - Login API endpoint
- `GET /dashboard` - Dashboard page (requires authentication)
- `POST /api/logout` - Logout API endpoint
- `GET /api/me` - Get current user info (for pi-ai)
- `GET /api/token` - Get auth token (for pi-ai)

## Authentication Flow

1. User submits login form via HTMX
2. Frontend sends credentials to PayloadCMS `/api/users/login`
3. On success, creates session with auth token
4. Sets secure HTTP-only cookie for session management
5. Redirects to dashboard
6. Token is accessible via API endpoints for pi-ai integration

## Technologies Used

- **FastAPI**: Modern Python web framework
- **HTMX**: HTML over the wire for dynamic interactions
- **Alpine.js**: Lightweight JavaScript framework
- **Jinja2**: Template engine for HTML rendering
- **Custom CSS**: Modern, responsive styling
- **PayloadCMS**: Headless CMS for backend authentication

## Configuration

The frontend can be configured by modifying variables in `main.py`:

- `PAYLOAD_CMS_URL`: PayloadCMS backend URL (default: `http://localhost:3000`)
- `SESSION_SECRET`: Secret key for session security (use environment variable in production)

## Development

### Running in Development Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### File Watching

The server will automatically reload when you make changes to:
- Python files
- Templates (when using `--reload`)

For CSS and JS changes, simply refresh the browser.

## Security Considerations

- Session cookies are HTTP-only and secure
- Tokens have expiration times
- CORS is configured for specific origins
- Input validation on both client and server side
- Protection against common web vulnerabilities

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure PayloadCMS backend is running on port 3000
2. **Login Failed**: Check PayloadCMS user credentials
3. **Static Files Not Loading**: Verify static file mounting in FastAPI
4. **HTMX Not Working**: Check browser console for JavaScript errors

### Logs

Check the FastAPI server logs for detailed error information:

```bash
# The server will log requests and errors to stdout
python main.py
```

## Contributing

1. Follow PEP 8 style guidelines for Python code
2. Use semantic HTML and modern CSS practices
3. Test authentication flow thoroughly
4. Ensure responsive design works on all devices
5. Document any new features or API endpoints

## License

This project is part of the PI-LMS ecosystem.
