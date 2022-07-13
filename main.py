# pylint: disable=consider-using-f-string,no-value-for-parameter

import time
from datetime import datetime
from json import dumps
from traceback import format_exc

from pymorphy2 import MorphAnalyzer
from redis import from_url
from vk_api.bot_longpoll import VkBotLongPoll

from functions import (check_word_existence, get_new_word, get_word_from_local,
                       msg, vk_session)
from models import Player
from settings import ADMIN, GROUP_ID, REDIS_URL

if __name__ == "__main__":
    longpoll = VkBotLongPoll(vk_session, GROUP_ID, 0)
    morph = MorphAnalyzer(lang='ru')

    redis_db = from_url(REDIS_URL)
    if not redis_db.get('everyday_word'):
        redis_db.set('everyday_word', get_word_from_local(), ex=86460)

    print('Бот запущен 🚀')

    while True:
        for event in longpoll.check():
            try:
                if event.t.value == 'message_new':
                    uid: int = event.message['peer_id']
                    text: str = event.message['text'].lower()
                    thisday_word = redis_db.get('everyday_word').decode()
                    print('📩 {}: получено сообщение «{}»'.format(uid, text))

                    if not text:
                        continue

                    player: Player = Player.get_or_create(id=uid, defaults={'cword': get_new_word()})[0]

                    # ==== АДМИН-ПАНЕЛЬ ====
                    if uid == ADMIN:
                        if 'data' in text:
                            if text == 'data':
                                response = Player.select().dicts().execute()
                            else:
                                act_id = text.split()[1]
                                if not act_id.isdigit():
                                    msg(ADMIN, 'Некорректный ввод.')
                                    continue
                                response = Player.select().where(Player.id == int(act_id)).dicts().execute()
                            msg(ADMIN, str('\n'.join([dumps(i, ensure_ascii=False) for i in list(response)])))
                            continue

                        if 'clear' in text:
                            action, act_id = text.split()[1], text.split()[2]
                            if not act_id.isdigit() or action not in ['all', 'everyday_stats', 'stats']:
                                msg(ADMIN, 'Некорректный ввод.')
                                continue

                            act_player = Player.get(Player.id == int(act_id))

                            if action == 'all':
                                res = act_player.delete_instance()
                                msg(ADMIN, 'Удалены данные о {} пользователях.'.format(res))
                            elif action == 'everyday_stats':
                                act_player.everyday_stats = dumps({i: 0 for i in (1, 2, 3, 4, 5, 6, 'wins', 'total')})
                                act_player.save()
                                msg(ADMIN, 'Статистика пользователя @id{} очищена.'.format(act_id))
                            elif action == 'stats':
                                act_player.stats = dumps({i: 0 for i in (1, 2, 3, 4, 5, 6, 'wins', 'total')})
                                act_player.save()
                                msg(ADMIN, 'Статистика пользователя @id{} очищена.'.format(act_id))
                            continue

                        if 'change everyday_word' in text:
                            word = text.split()[-1]
                            if word == 'everyday_word':
                                msg(ADMIN, 'Некорректный ввод.')
                                continue
                            s = (datetime(
                                datetime.now().year, datetime.now().month, datetime.now().day + 1, 0, 0
                            ) - datetime.now()).seconds
                            redis_db.set('everyday_word', word, ex=s + 60)
                            msg(ADMIN, 'Слово дня заменено на {}'.format(word))
                            continue

                        if 'помощь' in text or 'help' in text:
                            msg(uid, '– change everyday_word <word> — заменяет слово дня на word\n'
                                     '– clear {everyday_stats|stats|all} <id> — очищает данные о пользователе по id\n'
                                     '⠀ ⠀all — полностью пользователя\n'
                                     '⠀ ⠀everyday_stats — только статистику слова дня\n'
                                     '⠀ ⠀stats — только общую статистику\n'
                                     '– data [id] — выводит всех пользователей или одного по id из бд')
                    # ======================

                    if 'статистика' in text:
                        is_everyday = any(w in text for w in ['ворд', 'ежедн', 'слово дня'])
                        stats = player.get_everyday_stats() if is_everyday else player.get_stats()

                        msg(uid, ('Давай посмотрим, как ты играешь в {} 🎮\n'.format(
                            '«Ворд дня»' if is_everyday else 'свободном режиме'
                        )
                            + '1: {}\n2: {}\n3: {}\n4: {}\n5: {}\n6: {}\n'.format(
                            *[stats[str(i)] for i in range(1, 7)]
                        )
                            + 'Всего выиграно: {} из {} сыгранн{}.'.format(
                            stats['wins'], stats['total'],
                            'ой' if stats['total'] % 10 == 1 and stats['total'] % 100 != 11 else 'ых'
                        )))
                        continue

                    if any(w in text for w in ['ворд', 'ежедн', 'слово дня']):
                        if thisday_word.upper() in player.everyday_word:
                            s = (datetime(datetime.now().year, datetime.now().month, datetime.now().day + 1)
                                 - datetime.now()).seconds
                            h, m = s // 3600 - 3, s % 3600 // 60 + 1
                            p_h = ('' if h % 10 == 1 else 'а') if h // 10 in [0, 2] and h % 10 in range(1, 5) else 'ов'
                            p_m = ('у' if m % 10 == 1 else 'ы') if m // 10 in [0] + \
                                list(range(2, 7)) and m % 10 in range(1, 5) else ''
                            msg(uid, '{}\n\n'.format(player.everyday_word)
                                     + 'Кажется, сегодняшний ворд дня уже разгадан. Отдыхай до завтра!\n'
                                     'Новое слово через {} час{} и {} минут{} ⏳'.format(h, p_h, m, p_m))
                        else:
                            player.new_game(redis_db.get('everyday_word').decode())
                            msg(uid, 'Каждый день я загадываю любое слово из пяти букв, и все игроки его отгадывают. '
                                     'Только без спойлеров! 😉 \nСоревнуйся с друзьями и отгадывай быстрее них, '
                                     'тратя меньше попыток. \n\nИтак, играем в ворд дня! ⬜🟨🟩 Пиши первое слово...')
                            if not player.everyday_word:
                                player.toggle_push('everyday', True)
                        continue

                    if 'переключить пуши' in text:
                        player.toggle_push('everyday')
                        if player.get_push('everyday'):
                            msg(uid, 'Уведомления включены! 🔔 Уведомления о новом слове в «Ворде дня» '
                                     'каждый день в 10:00! 🕙')
                        else:
                            msg(uid, 'Уведомления отключены. 🔕 Если захотите включить их обратно, '
                                     'напишите «переключить пуши».')
                        continue

                    if text.split()[-1] in ['помощь', 'help']:
                        msg(uid, 'Разберёмся, что к чему:\n'
                                 '⠀– Напиши любое слово из пяти букв и веселье начнётся!\n'
                                 '⠀– Напиши «ворд дня», и мы сыграем в ежедневный режим «Ворд дня»!\n'
                                 '⠀– Напиши «статистика», чтобы узнать статистику своих игр.\n'
                                 '⠀– Напиши «статистика ворда дня», чтобы узнать статистику в режиме «Ворд дня».\n'
                                 '⠀– Напиши «помощь», чтобы вызвать эту прекрасную справку.\n'
                                 '⠀– Напиши «переключить пуши», чтобы включить или отключить ежедневные '
                                 'уведомления про «Ворд дня».\n\n'
                                 'Да начнётся веселье! 🏃🏻‍♂️'
                            )
                        continue

                    if not player.story:
                        player.story = ''

                    player.uword = text.split()[-1].lower()

                    if not check_word_existence(player.uword):
                        msg(uid, '{}Нет в словаре\n{}'.format(player.story,
                                                              player.used_letters))
                        continue

                    mask, lmask = '', ['*', '*', '*', '*', '*', '⠀']
                    for i in range(5):
                        if player.uword[i] == player.cword[i]:
                            mask += '🟩'
                            lmask = list(lmask)
                            if player.uword[i].upper() in lmask[lmask.index('⠀'):]:
                                lmask.remove(player.uword[i].upper())
                            lmask[i] = player.uword[i].upper()
                            lmask = ''.join(lmask)  # type: ignore
                            lmask += player.uword[i].upper()
                        elif (player.uword[i] in player.cword
                              and player.uword[:i].count(player.uword[i])
                              != player.cword.count(player.uword[i])
                              and player.uword[i]
                              != player.cword[player.uword.rfind(player.uword[i])]):
                            mask += '🟨'
                            lmask += player.uword[i].upper()
                        else:
                            mask += '⬜'
                            lmask += player.uword[i]

                        if player.uword[i].upper() in player.used_letters:
                            a = list(player.used_letters)
                            a.remove(player.uword[i].upper())
                            player.used_letters = ''.join(a)

                    msg(uid, '{}{}/6: {}⠀ ⠀{}\n{}'.format(player.story, player.guesses,
                                                          mask, ''.join(lmask), player.used_letters))

                    player.story += '{}/6: {}⠀ ⠀{}\n'.format(player.guesses, mask, ''.join(lmask))

                    if player.uword == player.cword:
                        num_to_word = {1: 'первой', 2: 'второй', 3: 'третьей',
                                       4: 'четвёртой', 5: 'пятой', 6: 'последней'}
                        if player.cword == thisday_word:
                            msg(uid, 'Это победа! Ты угадал ворд дня '
                                     '{} c {} попытки.\n'.format(player.cword.upper(), num_to_word[player.guesses]))
                            msg(uid, 'Делись своей победой в ворде дня с друзьми:\n\n{}'.format(player.story))
                            player.everyday_word = player.story
                        else:
                            msg(uid, 'Это победа! Ты завордлил слово '
                                     '{} с {} попытки. '.format(player.cword.upper(), num_to_word[player.guesses])
                                     + 'Так держать! ✊🏻\nБольше об этом слове: '
                                     'https://ru.wiktionary.org/wiki/{}.'.format(player.cword))
                        player.win(player.guesses, player.cword == thisday_word)
                    else:
                        player.increase_guesses()

                    if player.guesses == 7:
                        if player.cword == thisday_word:
                            msg(uid, 'Ты проиграл 😔 Загаданное слово: {0}.\n'.format(player.cword))
                            msg(uid, 'Делись ходом решения ворда дня с друзьями: \n\n{}'.format(player.story))
                            player.everyday_word = player.story
                        else:
                            msg(uid, 'Ты проиграл 😔 Загаданное слово: {0}.\n'.format(player.cword)
                                + 'Больше об этом слове: https://ru.wiktionary.org/wiki/{0}.'.format(player.cword))
                        player.lose(player.cword == thisday_word)

                    player.save()
            except Exception:
                msg(ADMIN, 'Поймали ошибку. Смотри трейсбек:\n\n{}'.format('\n'.join(format_exc().split('\n')[1:])))
        if (datetime.now().hour + 3, datetime.now().minute, datetime.now().second) == (0, 0, 0):
            redis_db.set('everyday_word', get_word_from_local(), ex=86460)
            time.sleep(1)
        if (datetime.now().hour + 3, datetime.now().minute, datetime.now().second) == (10, 0, 0):
            all_players: list[Player] = Player.select()
            thisday_word = redis_db.get('everyday_word').decode()
            for p in all_players:
                if thisday_word.upper() not in p.everyday_word and p.get_push('everyday'):
                    msg(p.id, 'Привет! В режиме «Ворд дня» появилось новое слово. Сыграем? Пиши «ворд дня» и погнали! '
                              '⬜🟨🟩\n\nОтключить ежедневные напоминания можно при помощи команды «переключить пуши».')
            time.sleep(1)
