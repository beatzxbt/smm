def calculate_mid_price(bba):
       best_bid, best_ask = bba[0][0], bba[1][0]
       return (best_ask + best_bid)/2

def calculate_weighted_mid_price(bba):
    imb = bba[0][1] / (bba[0][1] + bba[1][1])
    return bba[1][0] * imb + bba[0][0] * (1 - imb)