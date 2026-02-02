from .service_config import ServiceConfig


class ExternalServicePermission:
    """
    Manages permissions for using external services like LLMs.
    Implements Requirement #4: Request user permission before using external services.
    """
    
    def __init__(self, user_name='default_user'):
        """
        Initialize the external service permission manager.
        
        Args:
            user_name (str): Username from user_informations table
        """
        self.user_name = user_name
        self.config = ServiceConfig()
    
    def initialize(self):
        """Initialize the external service permission system."""
        try:
            self.config.initialize_table()
            return True
        except Exception as e:
            print(f"✗ Failed to initialize external service permissions: {e}")
            return False
    
    def has_permission(self, service_name='LLM'):
        """
        Check if user has granted permission for a specific service.
        This is used by the conditional logic in analysis_router.
        
        Args:
            service_name (str): Name of the external service
        
        Returns:
            bool | None: True/False if permission exists, None if no record
        """
        permission = self.config.get_permission(self.user_name, service_name)
        return permission
