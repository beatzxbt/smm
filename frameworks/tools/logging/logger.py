
from frameworks.tools.misc import current_datetime as now


class Logger:


    def __init__(self) -> None:
        pass

    
    def success(self, msg: str) -> None:
        print(f"{now()} | SUCCESS | {msg}")


    def info(self, msg: str) -> None:
        print(f"{now()} | INFO | {msg}")


    def debug(self, msg: str) -> None:
        print(f"{now()} | DEBUG | {msg}")

    
    def warning(self, msg: str) -> None:
        print(f"{now()} | WARNING | {msg}")


    def error(self, msg: str) -> None:
        print(f"{now()} | ERROR | {msg}")


    def critical(self, msg: str) -> None:
        print(f"{now()} | CRITICAL | {msg}")
