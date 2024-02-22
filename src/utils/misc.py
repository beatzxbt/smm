from time import time_ns, strftime

def datetime_now() -> str:
    return strftime("%Y-%m-%d %H:%M:%S") + f".{(time_ns()//1000) % 1000000:05d}"

def time_ms() -> int:
    return time_ns()//1_000_000