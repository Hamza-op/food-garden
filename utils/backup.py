"""
AuraPOS Professional - Backup and Restore Logic
"""
import os
import shutil
from datetime import datetime
from typing import List, Tuple, Dict
from config import DB_PATH, BACKUP_DIR


class BackupManager:
    """Handles database backup and restore operations."""
    
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Create backup directory if it doesn't exist."""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
        except Exception as e:
            print(f"Warning: Could not create backup dir: {e}")
    
    def create_backup(self, description: str = "") -> Tuple[bool, str]:
        """
        Create a backup of the database.
        Returns: (success, message/path)
        """
        try:
            self._ensure_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            desc_suffix = f"_{description}" if description else ""
            backup_name = f"aura_pos_backup_{timestamp}{desc_suffix}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Make sure source exists
            if not os.path.exists(DB_PATH):
                return False, f"Source database not found: {DB_PATH}"
            
            # Close any active connections by importing and closing db
            try:
                from database import db
                db.close()
            except Exception:
                pass
            
            # Copy the database file
            shutil.copy2(DB_PATH, backup_path)
            
            # Also copy WAL and SHM files if they exist
            wal_path = DB_PATH + "-wal"
            shm_path = DB_PATH + "-shm"
            if os.path.exists(wal_path):
                shutil.copy2(wal_path, backup_path + "-wal")
            if os.path.exists(shm_path):
                shutil.copy2(shm_path, backup_path + "-shm")
            
            # Reconnect
            try:
                from database import db
                db.connect()
            except Exception:
                pass
            
            return True, backup_path
            
        except Exception as e:
            return False, f"Backup failed: {str(e)}"
    
    def restore_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Restore database from a backup file.
        Returns: (success, message)
        """
        try:
            if not os.path.exists(backup_path):
                return False, f"Backup file not found: {backup_path}"
            
            # Import and close the database connection first
            try:
                from database import db
                db.close()
            except Exception as e:
                print(f"Warning closing db: {e}")
            
            # Create a safety backup before restore
            self._ensure_backup_dir()
            safety_path = os.path.join(self.backup_dir, f"pre_restore_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            if os.path.exists(DB_PATH):
                try:
                    shutil.copy2(DB_PATH, safety_path)
                except Exception as e:
                    print(f"Warning creating safety backup: {e}")
            
            # Remove existing db files
            try:
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                if os.path.exists(DB_PATH + "-wal"):
                    os.remove(DB_PATH + "-wal")
                if os.path.exists(DB_PATH + "-shm"):
                    os.remove(DB_PATH + "-shm")
            except Exception as e:
                return False, f"Could not remove old database: {e}"
            
            # Copy the backup to the main database path
            shutil.copy2(backup_path, DB_PATH)
            
            # Copy WAL and SHM if they exist with the backup
            if os.path.exists(backup_path + "-wal"):
                shutil.copy2(backup_path + "-wal", DB_PATH + "-wal")
            if os.path.exists(backup_path + "-shm"):
                shutil.copy2(backup_path + "-shm", DB_PATH + "-shm")
            
            # Reconnect database
            try:
                from database import db
                db.connect()
            except Exception as e:
                return False, f"Failed to reconnect after restore: {e}"
            
            return True, "Database restored successfully! Please reload the application."
            
        except Exception as e:
            return False, f"Restore failed: {str(e)}"
    
    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        try:
            self._ensure_backup_dir()
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.endswith(".db") and not filename.endswith("-wal") and not filename.endswith("-shm"):
                    if filename.startswith("aura_pos_backup"):
                        filepath = os.path.join(self.backup_dir, filename)
                        try:
                            stat = os.stat(filepath)
                            backups.append({
                                "filename": filename,
                                "path": filepath,
                                "size": stat.st_size,
                                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                            })
                        except Exception:
                            pass
            return sorted(backups, key=lambda x: x["created"], reverse=True)
        except Exception as e:
            print(f"Error listing backups: {e}")
            return []
    
    def delete_backup(self, backup_path: str) -> Tuple[bool, str]:
        """Delete a backup file."""
        try:
            if not os.path.exists(backup_path):
                return False, "Backup file not found"
            
            os.remove(backup_path)
            
            # Also remove WAL and SHM if they exist
            if os.path.exists(backup_path + "-wal"):
                os.remove(backup_path + "-wal")
            if os.path.exists(backup_path + "-shm"):
                os.remove(backup_path + "-shm")
                
            return True, "Backup deleted"
        except Exception as e:
            return False, f"Delete failed: {str(e)}"


# Global backup manager instance
backup_manager = BackupManager()