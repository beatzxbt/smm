import os

from framework.base.tools.logger.handlers.base import BaseLogHandler


class FileLogHandler(BaseLogHandler):
    """A log handler that appends log messages to a text file."""

    def __init__(self, filepath: str, create: bool = False) -> None:
        """Initialize the FileLogHandler with a target file path.

        Args:
            filepath (str): Path to the text file for appending logs. Must end with ".txt".

        Raises:
            ValueError: If the provided filepath does not end with ".txt".

        """
        super().__init__()

        if not filepath.endswith(".txt"):
            raise ValueError(
                f"Invalid filepath; expected string ending with '.txt' but got {filepath}"
            )

        # Check if file exists and create it if needed.
        if create:
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            if not os.path.exists(filepath):
                with open(filepath, "w"):
                    pass  # Create empty file
        self.filepath = filepath

    def push(self, buffer) -> None:
        with open(self.filepath, "a") as file:
            for msg in buffer:
                file.write(f"{msg}\n")
            file.flush()
