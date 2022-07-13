from random import choice, randint
from urllib.parse import unquote

from requests import exceptions, get
from vk_api import VkApi

from settings import VK_API_TOKEN


def check_connection() -> bool:
    '''Проверяет соединение с русским Викисловарём. Если соединение есть, то возвращает True, иначе — False.'''
    try:
        response = get('https://ru.wiktionary.org/')
        if not response.ok or response.status_code != 200:
            raise exceptions.ConnectionError
    except exceptions.ConnectionError:
        return False
    return True


def check_word_existence(word: str) -> bool:
    '''Проверяет, существует ли слово в введённой форме. Если существует, то возвращает True, иначе — False.

    Параметры
    ---------
    word: str
        слово для проверки
    '''

    if len(word) != 5:
        return False

    res = get('https://ru.wiktionary.org/w/api.php', {
        'action': 'opensearch',
        'search': word,
        'format': 'json'
    }).json()[1]

    if not res:
        return False
    if word.lower() in [w.lower() for w in res]:
        return True
    return False


def get_new_word() -> str:
    '''Получает новое слово из словаря пятибуквенных слов https://ru.wiktionary.org/wiki/Категория:Слова_из_5_букв/ru.
    При отсутствии доступа к словарю, получает слово из локального словаря.
    '''
    if not check_connection():
        return get_word_from_local()

    res = get('https://ru.wiktionary.org/wiki/Служебная:RandomInCategory/Слова_из_5_букв/ru')
    word = unquote(res.url).split('/')[-1]
    while (any(case in res.text for case in [
        'имя собственное', 'вульгарное', 'сленговое', ', одушевлённое',
        'разговорное', 'старинное', 'редкое', 'устаревшее', 'сокращённое'
    ])
            or 'существительное' not in res.text or word == word.title()):
        res = get('https://ru.wiktionary.org/wiki/Служебная:RandomInCategory/Слова_из_5_букв/ru')
        word = unquote(res.url).split('/')[-1]

    return word.lower()


def get_word_from_local() -> str:
    '''Получает новое слово из локальной базы пятибуквенных слов.'''

    with open('5lenwords_russian_base.txt', encoding='utf-8') as file:
        return choice(file.readlines()).strip()


def msg(id_: int, message: str = '', board: list = None, attach: str = '', parse: bool = True):
    '''Отправляет сообщение, используя текущую сессию vk_session.

    Параметры
    ---------
    id_: int
        ID пользователя ВКонтакте, которому отправляется сообщение
    message: str = ''
        текст сообщения
    board: list = None ([])
        клавиатура бота, отправляемая при необходимости
    attach: str = ''
        вложения, прикреплямые к сообщению при необходимости
    parse: bool = True
        надо ли парсить ссылки и крепить к ним сниппеты
    '''

    if board is None:
        board = []
    vk.messages.send(peer_id=id_, random_id=randint(-2 ** 31, 2 ** 31 - 1), message=message,
                     keyboard=board, dont_parse_links=not parse, attachment=attach)
    print('📨 {1}: отправлено сообщение «{0}»'.format(message.replace('\n', ' '), id_))


vk_session = VkApi(token=VK_API_TOKEN)
vk = vk_session.get_api()
