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
TYPE_VALUE = {
    "int": "целым числом",
    "float": "десятичным числом",
    "complex": "комплексным числом",
    "str": "строкой",
    "list": "списком",
    "tuple": "кортежем",
    "dict": "словарем",
}
ERROR_MESSEGE = ('Отсутствует обязательная переменная окружения:'
                 '{mis_tokens} Программа принудительно остановлена')


def check_tokens():
    """Проверят, что токены не пустые."""
    logging.debug('Старт проверки наличия токенов')
    variables = [('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
                 ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
                 ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)]
    missing_tokens = [var_name for var_name,
                      value in variables if value is None]
    if missing_tokens:
        logging.critical(ERROR_MESSEGE.format(mis_tokens=missing_tokens))
        return sys.exit(ERROR_MESSEGE.format(mis_tokens=missing_tokens))
    

def send_message(bot, message):
    """Отправка сообщений."""
    try:
        logging.debug('Старт отправки сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        message = f'Сообщения в телеграм не отправляются, {error}'
        logging.error(message)
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
        return response.json()
    except requests.RequestException as error:
        raise exceptions.ConnectinError(error)
    finally:
        if response.status_code != HTTPStatus.OK:
            raise exceptions.Not200ResponseCode(
                f'Сервер дал ответ: {response.status_code}')


def check_response(response):
    """Проверяет ответ АПИ на соответствие с документацией."""
    logging.debug('Старт проверки АПИ на соответствие документацией')
    if not isinstance(response, dict):
        response = TYPE_VALUE[type(response).__name__]
        raise TypeError(f'Ответ должен быть словарем, а не {response} ')
    if 'homeworks' not in response:
        raise exceptions.ResponseEmpty
    if not isinstance(response.get('homeworks'), list):
        homework = TYPE_VALUE[type(response.get('homeworks')).__name__]
        raise TypeError(f'Homeworks должен быть списком, а не {homework} ')
    logging.debug('Конец проверки АПИ на соответствие документацией')


def parse_status(homework):
    """Получает название и статус домашней работы."""
    logging.debug('Старт проверки статусов ДЗ')
    if 'homework_name' not in homework:
        raise TypeError('В ответе отсутсвует ключ homework_name')
    stutus = homework.get('status')
    if stutus not in (HOMEWORK_VERDICTS):
        raise ValueError(f'Неизвестный статус работы - {stutus}')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[stutus]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    message_status = " "
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get('homeworks')[0]
            homework_status_updated = homework['status']
            if homework_status_updated != message_status:
                message = parse_status(homework)
                send_message(bot, message)
                message_status = homework_status_updated
            else:
                logging.debug('Статус ДЗ не изменился')
            timestamp = response.get('current_date') or int(time.time())
        except exceptions.ResponseEmpty:
            logging.info('В ответе от API нет ключа homeworks')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if message_status != message:
                send_message(bot, message)
                message_status = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=('%(asctime)s, %(levelname)s, %(message)s,'
                'Файл - %(filename)s, Строка № %(lineno)d'),
        handlers=[logging.FileHandler('log.txt', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)])

    main()
