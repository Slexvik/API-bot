class TelegramError(Exception):
    """Ошибка телеги."""

    pass


class Not200ResponseCode(Exception):
    """Ответа от сервера не равен 200."""

    pass


class ConnectinError(Exception):
    """Не верный код ответа."""

    pass

