import pandas as pd
from time import time


class Misc:


    def current_datetime() -> pd.Timestamp:
        ct = time()
        dt = pd.to_datetime(ct, unit='s')
        return dt