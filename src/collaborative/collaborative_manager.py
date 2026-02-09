from .collaborative_storage import CollaborativeStorage
from .collaborative_display import CollaborativeDisplay
from .decorators import requires_collaborative

class CollaborativeManager:
    """
    Manager to handle user collaborative logic.
    Now supports proper data isolation using user_name.
    """

    def __init__(self, user_name: str = None):
        """
        Initialize CollaborativeManager for a specific user.
        
        Args:
            user_name: The username from user_informations table.
                       If None, manager will have limited functionality.
        """
        CollaborativeStorage.init_table()
        self.user_name = user_name
        if user_name:
            self.consent, self.collaborative, self.last_updated = self.get_preferences()
        else:
            self.consent, self.collaborative, self.last_updated = False, False, None

    def get_preferences(self):
        """Get preferences for the current user."""
        if not self.user_name:
            return False, False, None
        prefs = CollaborativeStorage.get_preferences(self.user_name)
        if prefs:
            return prefs
        return False, False, None

    def request_collaborative_if_needed(self) -> bool:
        """Check and request collaborative consent if not already granted."""
        if not self.user_name:
            return False
        if not self.collaborative:
            granted = CollaborativeDisplay.request_collaborative()
            CollaborativeStorage.update_collaborative(self.user_name, granted)
            self.collaborative = granted
        return self.collaborative

    def update_consent(self, consent: bool):
        """Update consent preference."""
        if not self.user_name:
            return
        CollaborativeStorage.update_consent(self.user_name, consent)
        self.consent = consent

    def update_collaborative(self, collaborative: bool):
        """Update collaborative preference."""
        if not self.user_name:
            return
        CollaborativeStorage.update_collaborative(self.user_name, collaborative)
        self.collaborative = collaborative
