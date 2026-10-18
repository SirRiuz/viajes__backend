PAYMENT_METHOD_CHOICES = [
    ("cash", "Cash"),
    ("transfer", "Transfer"),
]

PAYMENT_METHODS = frozenset(value for value, _label in PAYMENT_METHOD_CHOICES)
