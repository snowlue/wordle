from json import dumps, loads

from peewee import (IntegerField, Model, PostgresqlDatabase, SmallIntegerField,
                    TextField)
from playhouse.db_url import connect

from functions import get_new_word
from settings import DATABASE_URL

conn: PostgresqlDatabase = connect(DATABASE_URL, sslmode='require')


class BaseModel(Model):
    class Meta:
        database = conn


class Player(BaseModel):
    id = IntegerField(primary_key=True)
    cword = TextField()
    guesses = SmallIntegerField(default=1)
    story = TextField(default='')
    uword = TextField(default='')
    used_letters = TextField(default='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    stats = TextField(default=dumps({i: 0 for i in (1, 2, 3, 4, 5, 6, 'wins', 'total')}))
    everyday_word = TextField(default='')
    everyday_stats = TextField(default=dumps({i: 0 for i in (1, 2, 3, 4, 5, 6, 'wins', 'total')}))

    def new_game(self, cword: str = None):
        self.cword = get_new_word() if not cword else cword
        self.uword, self.guesses, self.story = '', 1, ''
        self.used_letters = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
        self.save()

    def increase_guesses(self):
        self.guesses += 1
        self.save()

    def win(self, guess: int, is_everyday: bool = False):
        stats_from_bd = loads(self.everyday_stats if is_everyday else self.stats)
        print(stats_from_bd)
        stats_from_bd[str(guess)] += 1
        stats_from_bd['wins'] += 1
        stats_from_bd['total'] += 1
        if is_everyday:
            self.everyday_stats = dumps(stats_from_bd)
        else:
            self.stats = dumps(stats_from_bd)
        self.new_game()

    def lose(self, is_everyday: bool = False):
        stats_from_bd = loads(self.everyday_stats if is_everyday else self.stats)
        stats_from_bd['total'] += 1
        if is_everyday:
            self.everyday_stats = dumps(stats_from_bd)
        else:
            self.stats = dumps(stats_from_bd)
        self.new_game()

    def get_stats(self):
        return loads(self.stats)

    def get_everyday_stats(self):
        return loads(self.everyday_stats)

    class Meta:
        table_name = 'Data'


if __name__ == "__main__":
    response = input('Создаём таблицы? (Y/N) ').lower()
    if response == 'y':
        conn.create_tables([Player], safe=False)
    # ПОЛЕ ДЛЯ СВОБОДНЫХ ЗАПРОСОВ
