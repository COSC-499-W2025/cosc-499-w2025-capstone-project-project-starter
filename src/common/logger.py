import logging
import sys

def setup_logger(name=__name__):
    logger = logging.getLogger(name)
    
    # Check if handlers already exist to avoid duplicate logging
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create console handler logging to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        # Format: Timestamp - Module Name - Log Level - Message
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
        
    return logger