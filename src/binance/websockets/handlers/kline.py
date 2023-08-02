import json
import numpy as np

from src.indicators.bbw import bbw


class BinanceKlineHandler:


    def __init__(self, sharedstate, data: json) -> None:
        self.ss = sharedstate
        self.data = data

    
    def process(self):
        """
        Used to attain close values and calculate volatility \n
        If candle close, shift array -1 and add new value \n
        Otherwise, update the most recent value \n
        """
        
        for candle in self.data:

            new_close = np.array([float(candle['close'])])

            if candle['confirm'] == True:
                self.ss.binance_klines = np.append(
                    arr=self.ss.binance_klines[1:], 
                    values=new_close, 
                    axis=0
                )

            else:
                self.ss.binance_klines[-1] = new_close
            
            self.ss.volatility_value = bbw(
                arr_in = self.ss.binance_klines, 
                length = self.ss.bb_length, 
                std = self.ss.bb_std
            )

            self.ss.volatility_value += self.ss.volatility_offset