

class BaseEndpoints:


    def mainnet1():
        return "https://api.bybit.com"


    def mainnet2():
        return "https://api.bytick.com"



class OrderEndpoints:


    def create_order():
        return "/v5/order/create"


    def create_batch():
        return "/unified/v3/private/order/create-batch"


    def amend_order():
        return "/v5/order/amend"


    def cancel_single():
        return "/v5/order/cancel"

        
    def cancel_all():
        return "/v5/order/cancel-all"

    