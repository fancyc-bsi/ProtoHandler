import logging
import colorlog


# Define the custom logging level for success
SUCCESS = 35

# Add the custom level to the logging module
logging.SUCCESS = SUCCESS
logging.addLevelName(SUCCESS, "SUCCESS")

# Custom logger class
class CustomLogger(logging.Logger):
    def success(self, msg, *args, **kwargs):
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, msg, args, **kwargs)

# Configure the logger
log = CustomLogger(__name__)

# Configure the logger
log.setLevel(logging.INFO)  # Set the default level to SUCCESS

# Define log formats with color
formatter = colorlog.ColoredFormatter(
    '%(log_color)s[%(levelname)s] %(message)s',  # Include the log level in the log message
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'WARNING': 'yellow',
        'INFO': 'blue',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
        'SUCCESS': 'green'  # Define a color for the SUCCESS level
    },
    secondary_log_colors={},
    style='%'
)

# Create a console handler and set the formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Add the console handler to the logger
log.addHandler(console_handler)

