import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import APIError, HTTPError, StatusResponceError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOK')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOK')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': 1549962000}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность работы переменных окружения."""
    check = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    if not check:
        error_message = 'Не один из ключей доступа не обнаружен'
        logging.critical(error_message)
        return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в чат Телеграмма."""
    try:
        logging.info('Начато отправление сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение {message} отправлено')
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка при отправке сообщения {message}: {error}')


def get_api_answer(timestamp):
    """Делает запрос к Эндпоинту."""
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        logging.info('Запрос к API')
        response = requests.get(**params_request)
        if response.status_code != HTTPStatus.OK:
            raise HTTPError('Код ответа не 200. {status}, {text}'.format(
                status=response.status_code,
                text=response.text
            ))
        return response.json()
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise APIError


def check_response(response: dict) -> dict:
    """Проверяет ответ API на соответствие документации."""
    logging.debug('Проверка сервиса на корректный ответ')
    if not isinstance(response, dict):
        raise TypeError('Ответ не является словарем')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Ответ не содержит ключ Homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('ДЗ не возвращается в виде списка')
    return homeworks


def parse_status(homework: dict) -> str:
    """Проверяет изменение статуса работы из данных полученных с API."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('В ответе API отсутствует ключ homework_name')
    if homework_status is None:
        raise KeyError('В ответе API отсутствует ключ homework_status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise StatusResponceError('Статус отличен от документированного')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    logging.basicConfig(
        format='%(asctime)s - %(funcName)s - %(lineno)s'
        '- %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    old_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                status = parse_status(homework)
            else:
                status = 'Нет изменений в статусе работы'
            if status != old_message:
                old_message = status
                send_message(bot, status)
            else:
                logging.debug('Нет изменений в статусе работы')
                timestamp = response.get('current_data')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != old_message:
                old_message = message
                send_message(bot, message)
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
