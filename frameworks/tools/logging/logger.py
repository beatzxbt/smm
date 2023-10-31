
from frameworks.tools.misc import current_datetime as now


class Logger:


    def __init__(self) -> None:
        pass

    
    def success(msg: str) -> None:
        print(f"{now()} | SUCCESS | {msg}")


    def info(msg: str) -> None:
        print(f"{now()} | INFO | {msg}")


    def debug(msg: str) -> None:
        print(f"{now()} | DEBUG | {msg}")


    def error(msg: str) -> None:
        print(f"{now()} | ERROR | {msg}")


    def critical(msg: str) -> None:
        print(f"{now()} | CRITICAL | {msg}")
