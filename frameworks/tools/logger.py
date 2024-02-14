from time import time_ns, strftime

def time_ms() -> int:
    return time_ns()//1_000_000

def time_now() -> str:
    return strftime("%Y-%m-%d %H:%M:%S") + f".{(time_ns()//1000) % 1000000:05d}"

class Logger:
    def success(msg: str) -> None:
        print(f"{time_now()} | SUCCESS | {msg}")

    def info(msg: str) -> None:
        print(f"{time_now()} | INFO | {msg}")

    def debug(msg: str) -> None:
        print(f"{time_now()} | DEBUG | {msg}")

    def warning(msg: str) -> None:
        print(f"{time_now()} | WARNING | {msg}")

    def error(msg: str) -> None:
        print(f"{time_now()} | ERROR | {msg}")

    def critical(msg: str) -> None:
        print(f"{time_now()} | CRITICAL | {msg}")