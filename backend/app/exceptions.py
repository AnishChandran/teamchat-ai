class ServiceUnavailableError(Exception):
    """Raised when a backing service (e.g. Firestore) is temporarily unavailable."""
