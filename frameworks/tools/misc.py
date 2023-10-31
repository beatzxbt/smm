
import pandas as pd
from time import time


def current_datetime() -> pd.Timestamp:
    return pd.to_datetime(time(), unit='s')
    