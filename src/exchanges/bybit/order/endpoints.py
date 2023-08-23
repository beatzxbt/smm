

class BaseEndpoints:

    MAINNET1 = "https://api.bybit.com"
    
    MAINNET2 = "https://api.bytick.com"


class OrderEndpoints:

    CREATE_ORDER = "/v5/order/create"

    CREATE_BATCH = "/unified/v3/private/order/create-batch"

    AMEND_ORDER = "/v5/order/amend"

    AMEND_BATCH = "/unified/v3/private/order/replace-batch"

    CANCEL_SINGLE = "/v5/order/cancel"

    CANCEL_BATCH = "/unified/v3/private/order/cancel-batch"

    CANCEL_ALL = "/v5/order/cancel-all"



    