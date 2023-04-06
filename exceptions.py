class HTTPError(Exception):
    """Статус доступа к адресу отличный от 200."""


class StatusResponceError(Exception):
    """Статус отличен от документированного."""


class APIError(Exception):
    """Ошибка при запросе API."""
    