from time import time_ns, strftime

def now() -> str:
    return strftime("%Y-%m-%d %H:%M:%S") + f".{(time_ns()//1000) % 1000000:05d}"

def ms() -> int:
    return time_ns()//1_000_000

class Logger:
    def success(msg: str) -> None:
        print(f"{now()} | SUCCESS | {msg}")

    def info(msg: str) -> None:
        print(f"{now()} | INFO | {msg}")

    def debug(msg: str) -> None:
        print(f"{now()} | DEBUG | {msg}")

    def warning(msg: str) -> None:
        print(f"{now()} | WARNING | {msg}")

    def error(msg: str) -> None:
        print(f"{now()} | ERROR | {msg}")

    def critical(msg: str) -> None:
        print(f"{now()} | CRITICAL | {msg}")