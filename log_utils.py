import logging
import os

LOG_FILE_NAME = "app.log" # Or import from config

def setup_logger(log_file_name=LOG_FILE_NAME, level=logging.INFO):
    """Sets up the root logger for the application."""
    # Ensure log directory exists if specified in path
    log_dir = os.path.dirname(log_file_name)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Basic configuration for logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_name), # Log to a file
            logging.StreamHandler()             # Log to console
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured. Log file: {log_file_name}")
    return logger

if __name__ == '__main__':
    # This demonstrates how other modules will use the logger
    # In other files, you'd do:
    # import logging
    # logger = logging.getLogger(__name__)
    # logger.info("This is a test message from another module.")
    
    app_logger = setup_logger() # Setup once in your main application entry point
    app_logger.info("Test info message from log_utils.")
    app_logger.warning("Test warning message.")
    app_logger.error("Test error message.")

    # Example of how other modules would use it after setup_logger() is called once
    another_module_logger = logging.getLogger("MyOtherModule")
    another_module_logger.info("Message from another module.")
