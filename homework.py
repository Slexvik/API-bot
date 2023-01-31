import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format=('%(asctime)s, %(levelname)s, %(message)s,'
            'Файл - %(filename)s, Строка № %(lineno)d'),
    handlers=[logging.FileHandler('log.txt', encoding='UTF-8'),
              logging.StreamHandler(sys.stdout)])


def check_tokens():
    """Проверят, что токены не пустые."""
    logging.info("Старт проверки наличия токенов")
    variables = [("PRACTICUM_TOKEN", PRACTICUM_TOKEN),
                 ("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
                 ("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)]
    missing_tokens = [var_name for var_name,
                      value in variables if value is None]
    if missing_tokens:
        logging.critical("Отсутствует обязательная переменная окружения:"
                         f"missing_tokens"
                         "Программа принудительно остановлена")
        return sys.exit()
    return True


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(error)
        raise exceptions.TelegramError('Сообщения в телеграм не отправляются,',
                                       error)
    else:
        logging.debug(f'Сообщение отправлено: {message}')


def get_api_answer(timestamp):
    """Опрашиваем эндпоинт, возвращаем словарь с ДЗ."""
    logging.info("Старт запуская обращения к АПИ")
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=payload)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.Not200ResponseCode(
                f'Сервер дал ответ: {response.status_code}')
        return response.json()
    except Exception as error:
        raise exceptions.ConnectinError(error)


def check_response(response):
    """Проверяет ответ АПИ на соответствие с документацией."""
    logging.info("Старт проверки АПИ на соответствие документацией")
    if not isinstance(response, dict):
        raise TypeError('Ответ не содержит словаря.')
    if not isinstance(response.get('homeworks'), list):
        print(type(response.get('homeworks')))
        raise TypeError('Homeworks не является списком.')
    return True


def parse_status(homework):
    """Получает название и статус домашней работы."""
    logging.info("Старт проверки статусов ДЗ")
    if 'homework_name' not in homework:
        raise TypeError('В ответе отсутсвует ключ homework_name')
    stutus = homework.get('status')
    if stutus not in (HOMEWORK_VERDICTS):
        raise ValueError(f'Неизвестный статус работы - {stutus}')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS[stutus]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info("Начало проверки")
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    homeworks_status = " "
    message_error = " "
    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp)
            check_response(response)
            if response.get('homeworks'):
                homework = response.get('homeworks')[0]
                homework_status_updated = homework.get('status')
                if homework_status_updated != homeworks_status:
                    message = parse_status(homework)
                    send_message(bot, message)
                    homeworks_status = homework_status_updated
                else:
                    logging.debug('Статус ДЗ не изменился')
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message_error != message:
                send_message(bot, message)
                message_error = message
            logging.error(message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
