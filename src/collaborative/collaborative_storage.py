"""
CollaborativeStorage - Wrapper around user_preferences for collaborative features.
Now uses user_name for proper data isolation instead of hardcoded user_id.
"""
from database.user_preferences import (
    init_user_preferences_table,
    update_user_preferences,
    get_user_preferences,
    update_user_collaboration,
    get_user_collaboration
)
from config.db_config import with_db_cursor

class CollaborativeStorage:
    """
    Handles storage and retrieval of user consent and collaborative preferences.
    Uses user_name for data isolation.
    """

    @staticmethod
    def init_table():
        """Create user_preferences table if it does not exist."""
        return init_user_preferences_table()

    @staticmethod
    def update_consent(user_name: str, consent: bool):
        """
        Update user consent preference.
        
        Args:
            user_name: The username from user_informations table
            consent: The consent preference value
        """
        return update_user_preferences(user_name, consent)

    @staticmethod
    def update_collaborative(user_name: str, collaborative: bool):
        """
        Update user collaborative preference.
        
        Args:
            user_name: The username from user_informations table
            collaborative: The collaboration preference value
        """
        return update_user_collaboration(user_name, collaborative)

    @staticmethod
    def get_preferences(user_name: str):
        """
        Return tuple (consent: bool, collaborative: bool, last_updated: datetime).
        
        Args:
            user_name: The username from user_informations table
            
        Returns:
            tuple: (consent, collaborative, last_updated) or None
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT consent, collaborative, last_updated 
                    FROM user_preferences 
                    WHERE user_name = %s;
                """, (user_name,))
                result = cursor.fetchone()
            return result
        except Exception:
            return None
