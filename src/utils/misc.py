
import pandas as pd
from time import time


def curr_dt() -> pd.Timestamp:
    return pd.to_datetime(time(), unit='s')
    