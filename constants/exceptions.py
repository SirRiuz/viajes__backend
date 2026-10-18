class ErrorMessages:
    """System error messages."""

    SECRET_KEY_TOO_SHORT = (
        "SECRET_KEY must be at least 50 random characters "
        "(python -c 'import secrets; print(secrets.token_urlsafe(64))')."
    )
    ALLOWED_HOSTS_WILDCARD = "ALLOWED_HOSTS must list the real hosts, not «*»."
    ACCESS_DENIED_SUPERUSER_REQUIRED = "Access denied."
    TOO_MANY_LOGIN_ATTEMPTS = "Too many attempts. Try again later."
    LEGACY_MIGRATIONS_MISSING = (
        "The database still uses the old per-app tables, but app/migrations "
        "is empty. Run `make migrations` first, then `make migrate`."
    )


class ValidationExceptions:
    """Messages returned to the client by the GraphQL mutations."""

    DRIVER_NOT_FOUND = "Driver not found"
    ROUTE_NOT_FOUND = "Route not found"
    ROUTE_DELETED = "Route deleted successfully"
    VESSEL_NOT_FOUND = "Vessel not found"
    TRIP_NOT_FOUND = "Trip not found"
    TRIP_NOT_FOUND_OR_DELETED = "Trip not found or already deleted"
    TRIP_DELETED = "Trip deleted successfully"
    TICKET_NOT_FOUND = "Ticket not found"
    TICKET_NOT_FOUND_OR_DELETED = "Ticket not found or already deleted"
    TICKET_DELETED = "Ticket deleted successfully"
    INVALID_PAYMENT_METHOD = "Invalid payment method"
