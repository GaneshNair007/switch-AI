# Feature flags for checkout-service
# PR #482 enables dynamic pricing for staged rollout

FEATURE_DYNAMIC_PRICING = True
PRICING_CALCULATION_MODE = "server_authoritative"
MAX_CART_ITEM_LIMIT = 50
DEFAULT_TAX_RATE = 0.0825

