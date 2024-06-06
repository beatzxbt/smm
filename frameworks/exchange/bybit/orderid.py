import string
import numpy as np

from frameworks.exchange.base.orderid import OrderIdGenerator

class BybitOrderIdGenerator(OrderIdGenerator):
    legal_chars = np.array([i for i in string.ascii_letters + string.digits + "-_"])

    def __init__(self) -> None:
        super().__init__(36)

    def generate_random_str(self, length: int) -> str:
        return ''.join(np.random.choice(self.legal_chars, length).tolist())