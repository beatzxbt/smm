from time import time_ns, strftime

def now() -> str:
    return strftime("%Y-%m-%d %H:%M:%S") + f".{(time_ns()//1000) % 1000000:05d}"

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
