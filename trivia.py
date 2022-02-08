from pickletools import string1
from errbot import BotPlugin, botcmd, arg_botcmd
from errbot.backends.base import Room
from functools import partial
from threading import Event, Timer
from enum import Enum
import random
import math
import sqlite3
from contextlib import closing
from itertools import chain

CONFIG_TEMPLATE = {
    "DATABASE_PATH": "./trivia.db",
    "HINT_DELAY_SECONDS": 5,
    "QUESTION_DELAY_SECONDS": 5,
}

class TriviaPlugin(BotPlugin):
    def activate(self) -> None:
        super().activate()
        self._games = dict()

        # TODO prevent threading issues re-using this connection between timer threads
        database_path = self.config['DATABASE_PATH']
        self.db_connection = sqlite3.connect(database_path, check_same_thread=False)

    def deactivate(self) -> None:
        super().deactivate()
        self.db_connection.close()

    def get_configuration_template(self):
        return CONFIG_TEMPLATE

    def configure(self, configuration):
        if configuration is not None and configuration != {}:
            config = dict(chain(CONFIG_TEMPLATE.items(), configuration.items()))
        else:
            config = CONFIG_TEMPLATE

        super(TriviaPlugin, self).configure(config)

    @botcmd(admin_only=True)
    @arg_botcmd("num_questions", type = int, default = 10)
    def trivia_start(self, message, num_questions = 10):
        if not isinstance(message.to, Room):
           # Ignore private messages
           return

        room_name = str(message.to)
        hint_delay_seconds = self.config['HINT_DELAY_SECONDS']
        question_delay_seconds = self.config['QUESTION_DELAY_SECONDS']
        game = self._games.get(room_name, Game(self.db_connection, room_name, num_questions, hint_delay_seconds, question_delay_seconds, partial(self.send, message.to)))
        if game.in_progress:
            # A trivia game is already in progress in room
            return

        game.start(hint_delay_seconds, question_delay_seconds)
        self._games[room_name] = game

        self.log.info(f"Trivia game started in {message.to} by {message.frm}")

    @botcmd(admin_only=True)
    def skip(self, message, args):
        room_name = str(message.to)
        game = self._games.get(room_name, None)
        if game is None:
            # No trivia game is in progress in the room
            return

        game.skip()

    @botcmd(admin_only=True)
    def trivia_stop(self, message, _):
        if not isinstance(message.to, Room):
           # Ignore private messages
           return

        room_name = str(message.to)
        game = self._games.pop(room_name, None)
        if game is None or not game.in_progress:
            # No trivia game is in progress in the room
            return

        game.stop()
        self.log.info(f"Trivia game stopped in {message.to} by {message.frm}")

    @botcmd(admin_only=True)
    @arg_botcmd("alias", type = str)
    @arg_botcmd("nick", type = str)
    def trivia_alias_add(self, message, nick: str, alias: str):
        Aliases(self.db_connection).add_alias(nick, alias)

    @botcmd(admin_only=True)
    @arg_botcmd("alias", type = str)
    @arg_botcmd("nick", type = str)
    def trivia_alias_remove(self, _, nick: str, alias: str):
        Aliases(self.db_connection).remove_alias(nick, alias)

    @botcmd(admin_only=True)
    @arg_botcmd("nick", type = str)
    def trivia_alias_list(self, _, nick: str):
        aliases = Aliases(self.db_connection).list_aliases(nick)
        yield f"Aliases for '{nick}': {aliases}"

    @botcmd()
    def hof(self, message, _):
        if not isinstance(message.to, Room):
           # Ignore private messages
           return

        room_name = str(message.to)
        hall_of_fame = GameStatistics(self.db_connection, room_name).hall_of_fame()
        yield f"Hall of Fame for {room_name}: {hall_of_fame}"

    @botcmd(split_args_with=None)
    def stats(self, message, args):
        if not isinstance(message.to, Room):
           # Ignore private messages
           return

        room_name = str(message.to)
        user_name = args[0] if len(args) > 0 else message.frm.nick
        points = GameStatistics(self.db_connection, room_name).get_points_for_user(user_name)
        yield f"Statistics for {user_name}: {points} point(s)"

    def callback_message(self, message):
        room_name = str(message.to)
        game = self._games.get(room_name, None)
        if game is None:
            # No trivia game is in progress in the room
            return

        game.answer(message.frm.nick, message.body)

class HintDifficulty(Enum):
    HARD = 1
    MEDIUM = 2
    EASY = 3

class Question:
    def __init__(self, question: str, answer: str):
        self.question = question
        self.answer = answer
        self.question_completed = Event()
        self._init_hints()

    def _init_hints(self) -> None:
        indexes = [i for i, c in enumerate(self.answer) if not c.isspace()]

        indexes_hard_hint = random.sample(indexes, math.floor(0.7 * len(indexes)))
        indexes_medium_hint = random.sample(indexes_hard_hint, math.floor(0.7 * len(indexes_hard_hint)))
        indexes_easy_hint = random.sample(indexes_medium_hint, math.floor(0.7 * len(indexes_medium_hint)))

        hint_hard = "".join(['-' if i in indexes_hard_hint else c for i, c in enumerate(self.answer)])
        hint_medium = "".join(['-' if i in indexes_medium_hint else c for i, c in enumerate(self.answer)])
        hint_easy = "".join(['-' if i in indexes_easy_hint else c for i, c in enumerate(self.answer)])

        self.hints = dict()
        self.hints[HintDifficulty.HARD] = hint_hard
        self.hints[HintDifficulty.MEDIUM] = hint_medium
        self.hints[HintDifficulty.EASY] = hint_easy

class Aliases: 
    def __init__(self, db_connection: sqlite3.Connection):
        self.db_connection = db_connection

    def add_alias(self, user_name: str, alias: str) -> None:
        with closing(self.db_connection.cursor()) as cursor:
            user_id = self._get_or_create_user_id_by_name(cursor, user_name)
            alias_user_id = self._get_or_create_user_id_by_name(cursor, alias)

            # TODO prevent circular aliases

            cursor.execute("INSERT OR IGNORE INTO UserAliases ( OriginalId, AliasId ) VALUES ( ?, ? )", [user_id, alias_user_id])
            self.db_connection.commit()

    def remove_alias(self, user_name: str, alias: str) -> None:
        with closing(self.db_connection.cursor()) as cursor:
            user_id = self._get_user_id_by_name(cursor, user_name)
            alias_user_id = self._get_user_id_by_name(cursor, alias)

            if user_id is None or alias_user_id is None:
                return

            cursor.execute("DELETE FROM UserAliases WHERE OriginalId = ? AND AliasId = ?", [user_id, alias_user_id])
            self.db_connection.commit()

    def list_aliases(self, user_name: str):
        with closing(self.db_connection.cursor()) as cursor:
            user_id = self._get_user_id_by_name(cursor, user_name)

            query = """
                SELECT Name
                FROM Users
                WHERE Id IN ( SELECT AliasId FROM UserAliases WHERE OriginalId = :user_id )
            """

            cursor.execute(query, { "user_id": user_id })
            rows = cursor.fetchall()
            return ", ".join(row[0] for _, row in enumerate(rows))

    def _get_user_id_by_name(self, cursor: sqlite3.Cursor, user_name: str) -> int:
        cursor.execute("SELECT Id FROM Users WHERE Name = ?", [user_name])
        result = cursor.fetchone()
        return None if result is None else result[0]

    def _get_or_create_user_id_by_name(self, cursor: sqlite3.Cursor, user_name: str) -> int:
        cursor.execute("SELECT Id FROM Users WHERE Name = ?", [user_name])
        result = cursor.fetchone()
        if result is not None:
            return result[0]

        cursor.execute("INSERT INTO Users ( Name ) VALUES ( ? )", [user_name])
        return cursor.lastrowid

class Questions:
    def __init__(self, db_connection: sqlite3.Connection, num_questions: int):
        self.db_connection = db_connection
        self.num_questions = num_questions

    def __iter__(self):
        with closing(self.db_connection.cursor()) as cursor:
            num_questions = round(self.num_questions * 0.7)
            questions = self._get_questions(cursor, num_questions)
            num_scrambled_words = min(round(self.num_questions * 0.3), self.num_questions - num_questions)
            scrambled_words = self._get_scrambled_word_questions(cursor, num_scrambled_words)

            lst = list(chain(questions, scrambled_words))
            random.shuffle(lst)
            return iter(lst)


    def _get_questions(self, cursor: sqlite3.Cursor, n: int):
        query = """
            SELECT Question, Answer
            FROM Questions
            ORDER BY RANDOM() LIMIT ?
        """
        for row in cursor.execute(query, [n]):
            yield Question(row[0], row[1])

    def _get_scrambled_word_questions(self, cursor: sqlite3.Cursor, n: int):
        query = """
            SELECT LOWER(Word)
            FROM ScrambledWords
            ORDER BY RANDOM() LIMIT ?
        """
        for row in cursor.execute(query, [n]):
            word = row[0]
            yield Question(f"Unscramble this word: {self._scramble(word)}", word)

    def _scramble(self, word):
        l = list(word)
        random.shuffle(l)
        return " ".join(l)


class GameStatistics:
    def __init__(self, db_connection: sqlite3.Connection, game_name: str):
        self.db_connection = db_connection
        self.game_name = game_name
        self._statistics = dict()

    def add_point_to_user(self, user_name: str) -> None:
        current_points = self._statistics.get(user_name, 0)
        self._statistics[user_name] = current_points + 1

    def save(self) -> None:
        with closing(self.db_connection.cursor()) as cursor:
            game_id = self._get_or_create_game_id_by_name(cursor, self.game_name)

            for user_name, points in self._statistics.items():
                user_id = self._get_or_create_user_id_by_name(cursor, user_name)
                
                query = """
                    INSERT INTO GameStatistics ( GameId, UserId, Points ) VALUES ( :game_id, :user_id, :points )
                    ON CONFLICT ( GameId, UserId ) DO UPDATE SET Points = Points + :points
                """

                cursor.execute(query, { "game_id": game_id, "user_id": user_id, "points": points })

    def hall_of_fame(self) -> str:
        with closing(self.db_connection.cursor()) as cursor:
            game_id = self._get_or_create_game_id_by_name(cursor, self.game_name)
            
            query = """
                SELECT u.Name as UserName, SUM(gs.Points) AS Points
                FROM GameStatistics AS gs
                INNER JOIN Users AS u ON u.Id = gs.UserId
                LEFT JOIN UserAliases ua ON ua.OriginalId = u.Id
                WHERE gs.GameId = :game_id
                GROUP BY COALESCE(ua.AliasId, u.Id)
                ORDER BY Points DESC
                LIMIT 10
            """

            cursor.execute(query, { "game_id": game_id })
            rows = cursor.fetchall()

            self.db_connection.commit()
            return ", ".join("{}. {} : {} point(s)".format(index + 1, row[0], row[1]) for index, row in enumerate(rows))

    def get_points_for_user(self, user_name: str) -> int:
        with closing(self.db_connection.cursor()) as cursor:
            game_id = self._get_or_create_game_id_by_name(cursor, self.game_name)
            user_id = self._get_user_id_by_name(cursor, user_name)

            if user_id is None:
                return 0

            query = """
                SELECT SUM(gs.Points)
                FROM GameStatistics AS gs
                LEFT JOIN UserAliases ua ON ua.OriginalId = gs.UserId
                WHERE gs.GameId = :game_id AND COALESCE(ua.AliasId, gs.UserId) = :user_id
            """

            cursor.execute(query, { "game_id": game_id, "user_id": user_id })
            result = cursor.fetchone()

            self.db_connection.commit()
            return 0 if result is None or result[0] is None else result[0]

    def __str__(self):
        items = list(self._statistics.items())
        items.sort(key = lambda x:x[1], reverse = True)
        return ", ".join("{}: {} point(s)".format(*item) for item in items)

    def __len__(self):
        return len(self._statistics)

    def _get_or_create_game_id_by_name(self, cursor: sqlite3.Cursor, game_name: str) -> int:
        cursor.execute("SELECT Id FROM Games WHERE Name = ?", [game_name])
        game_id = cursor.fetchone()

        if game_id is not None:
            return game_id[0]

        cursor.execute("INSERT INTO Games ( Name ) VALUES ( ? )", [game_name])
        return cursor.lastrowid

    def _get_user_id_by_name(self, cursor: sqlite3.Cursor, user_name: str) -> int:
        cursor.execute("SELECT Id FROM Users WHERE Name = ?", [user_name])
        user_id = cursor.fetchone()
        return user_id[0] if user_id is not None else None

    def _get_or_create_user_id_by_name(self, cursor: sqlite3.Cursor, user_name: str) -> int:
        cursor.execute("SELECT Id FROM Users WHERE Name = ?", [user_name])
        user_id = cursor.fetchone()
        if user_id is not None:
            return user_id[0]

        cursor.execute("INSERT INTO Users ( Name ) VALUES ( ? )", [user_name])
        return cursor.lastrowid

class Game:
    def __init__(self, db_connection: sqlite3.Connection, game_name: str, hint_delay_seconds: int, question_delay_seconds: int, num_questions: int, send_message):
        self.db_connection = db_connection
        self.game_name = game_name
        self.num_questions = num_questions
        self.send_message = send_message
        self.in_progress = False
        self.hint_delay_seconds = hint_delay_seconds
        self.question_delay_seconds = question_delay_seconds
        self.question_timer = Timer(question_delay_seconds, self._ask_question)
        self.current_question = None

    def answer(self, user_name: str, guess: str) -> None:
        if self.current_question is None:
            return

        if guess.casefold() == self.current_question.answer.casefold():
            self.send_message("Correct!")
            self.current_question.question_completed.set()
            self.game_statistics.add_point_to_user(user_name)

    def skip(self):
        self.current_question.question_completed.set()

    def start(self, hint_delay_seconds: int, question_delay_seconds: int) -> None:
        self.in_progress = True
        self.hint_delay_seconds = hint_delay_seconds
        self.question_delay_seconds = question_delay_seconds
        self.game_statistics = GameStatistics(self.db_connection, self.game_name)
        self.questions = iter(Questions(self.db_connection, self.num_questions))
        self._restart_question_timer()

    def stop(self) -> None:
        self.in_progress = False
        self.question_timer.cancel()

    def _ask_question(self) -> None:
        current_question = next(self.questions, None)
        if current_question is None:
            self.in_progress = False

            if len(self.game_statistics) > 0:
                self.send_message(f"Game finished! Stats: {self.game_statistics}")
            else:
                self.send_message(f"Game finished!")

            self.game_statistics.save()
            self.db_connection.commit()
            return

        self.current_question = current_question

        if self.in_progress:
            self.send_message(current_question.question)

        self._send_hint(current_question, HintDifficulty.HARD)
        self._send_hint(current_question, HintDifficulty.MEDIUM)
        self._send_hint(current_question, HintDifficulty.EASY)
        self._send_answer(current_question)
        self._restart_question_timer()

    def _restart_question_timer(self) -> None:
        if not self.in_progress:
            return
        
        self.question_timer.cancel()
        self.question_timer = Timer(self.question_delay_seconds, self._ask_question)
        self.current_question = None
        self.question_timer.start()

    def _send_answer(self, question: Question) -> None:
        if question is None:
            return

        question.question_completed.wait(self.hint_delay_seconds)
        if not question.question_completed.is_set() and self.in_progress:
            self.send_message(f"Answer: {question.answer}")

    def _send_hint(self, question: Question, difficulty: HintDifficulty) -> None:
        if question is None:
            return

        question.question_completed.wait(self.hint_delay_seconds)
        if not question.question_completed.is_set() and self.in_progress:
            hint = question.hints[difficulty]
            self.send_message(f"Hint: {hint}")
