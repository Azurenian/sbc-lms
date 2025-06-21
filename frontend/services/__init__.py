"""PI-Frontend Services Module

This module provides shared services for the PI-LMS ecosystem,
including authentication services that can be used by both
the frontend application and pi-ai.
"""

from .auth_service import (
    PIAuthService,
    get_auth_service,
    get_auth_token,
    authenticate,
    get_current_user,
    is_authenticated,
    logout
)

__all__ = [
    'PIAuthService',
    'get_auth_service',
    'get_auth_token',
    'authenticate',
    'get_current_user',
    'is_authenticated',
    'logout'
]
