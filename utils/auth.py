"""
AuraPOS Professional - Authentication Logic
"""
import bcrypt
from typing import Optional, Dict, Any
from database import db


class AuthManager:
    """Handles user authentication and session management."""
    
    def __init__(self):
        self._current_user: Optional[Dict[str, Any]] = None
    
    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        """Get the currently logged-in user."""
        return self._current_user
    
    @property
    def is_authenticated(self) -> bool:
        """Check if a user is logged in."""
        return self._current_user is not None
    
    @property
    def is_admin(self) -> bool:
        """Check if current user is an admin."""
        return self._current_user is not None and self._current_user.get("role") == "Admin"
    
    def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        Attempt to log in a user.
        Returns: (success, message)
        """
        try:
            user = db.get_user(username)
            if user is None:
                return False, "Invalid username or password"
            
            if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                self._current_user = {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"]
                }
                return True, f"Welcome, {username}!"
            else:
                return False, "Invalid username or password"
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    def logout(self):
        """Log out the current user."""
        self._current_user = None
    
    def register_user(self, username: str, password: str, role: str = "Staff") -> tuple[bool, str]:
        """
        Register a new user (admin only operation).
        Returns: (success, message)
        """
        if not self.is_admin:
            return False, "Only admins can register new users"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        if role not in ("Admin", "Staff"):
            return False, "Invalid role"
        
        try:
            existing = db.get_user(username)
            if existing:
                return False, "Username already exists"
            
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            if db.add_user(username, password_hash, role):
                return True, f"User '{username}' created successfully"
            else:
                return False, "Failed to create user"
        except Exception as e:
            return False, f"Registration error: {str(e)}"
    
    def change_password(self, old_password: str, new_password: str) -> tuple[bool, str]:
        """
        Change the current user's password.
        Returns: (success, message)
        """
        if not self.is_authenticated:
            return False, "Not logged in"
        
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters"
        
        try:
            user = db.get_user(self._current_user["username"])
            if not bcrypt.checkpw(old_password.encode(), user["password_hash"].encode()):
                return False, "Current password is incorrect"
            
            new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            cursor = db.connection.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, self._current_user["id"])
            )
            db.connection.commit()
            return True, "Password changed successfully"
        except Exception as e:
            return False, f"Error changing password: {str(e)}"


# Global auth instance
auth = AuthManager()
