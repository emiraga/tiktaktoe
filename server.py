import json
import threading
import random
import string
import time
import sqlite3
import os
from flask import Flask, Response, redirect, request, jsonify

games = {}


class Game:
    def __init__(self, game_type):
        self.password = {'X': None, 'O': None}
        self.squares = [None] * 9
        self.x_is_next = True
        self.x_goes_next = False
        self.o_connected = False
        self.score_for_x = 0
        self.score_for_o = 0
        self.condition = threading.Condition()
        self.game_type = game_type
        self.last_ping_response = {'X': 0, 'O': 0}
        self.messages = []

    def update_score_new_move(self):
        winner = self.compute_status()['winning_player']
        if winner == 'X':
            self.score_for_x += 1
        elif winner == 'O':
            self.score_for_o += 1

    def compute_status(self):
        player = calculate_winner(self.squares)
        winning_player = None
        if player:
            winning_player = player
            is_restartable = True
        elif calculate_is_board_filled(self.squares):
            is_restartable = True
        else:
            is_restartable = False
        return {
            'winning_player': winning_player,
            'is_restartable': is_restartable,
        }

    def play_computer_move(self):
        move = compute_best_move(self.squares)
        if move is not None:
            self.squares[move] = 'O'
            self.x_is_next = True

    def assign_password(self, player_code, player_password):
        self.password[player_code] = player_password

    def save_new_game_to_database(self):
        with sqlite3.connect('games.db') as con:
            cur = con.cursor()
            cur.execute('''INSERT INTO game (
                    password, squares, x_is_next, x_goes_next, 
                    o_connected, score_for_x, score_for_o,
                    game_type, last_ping_response, messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (json.dumps(self.password), json.dumps(self.squares), int(self.x_is_next), 
                    int(self.x_goes_next), int(self.o_connected), self.score_for_x, self.score_for_o,
                    self.game_type, json.dumps(self.last_ping_response), json.dumps(self.messages)))
            con.commit()
            self.game_id = cur.lastrowid

    def update_record_in_database(self):
        with sqlite3.connect('games.db') as con:
            cur = con.cursor()
            cur.execute(
                '''UPDATE game SET 
                    password = ?, squares = ?, x_is_next = ?, 
                    x_goes_next = ?, o_connected = ?, score_for_x = ?, 
                    score_for_o = ?, game_type = ?, last_ping_response = ?, messages = ?
                WHERE game_id = ?''',
                (json.dumps(self.password), json.dumps(self.squares), int(self.x_is_next), 
                    int(self.x_goes_next), int(self.o_connected), self.score_for_x, self.score_for_o,
                    self.game_type, json.dumps(self.last_ping_response), json.dumps(self.messages), self.game_id)
            )
            con.commit()


def compute_best_move(squares):
    best_score=-1000
    best_move=None
    for i in range(9):
        if not squares[i]:
            squares[i]='O'
            score=minimax(squares,False)
            squares[i]=None
            if score>best_score:
                best_score=score
                best_move=i
    return best_move
            
def minimax(squares, is_maximizing):
    winner = calculate_winner(squares)
    if winner == 'X':
        return -1
    elif winner == 'O':
        return 1
    if calculate_is_board_filled(squares):
        return 0
    if is_maximizing:
        best_score=-1000
        for i in range(9):
            if not squares[i]:
                squares[i]='O'
                score=minimax(squares,False)
                squares[i]=None
                if score>best_score:
                    best_score=score
        return best_score
    best_score=1000
    for i in range(9):
        if not squares[i]:
            squares[i]='X'
            score=minimax(squares,True)
            squares[i]=None
            if score<best_score:
                best_score=score
    return best_score


def get_new_password():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(10))


def load_games_from_database():
    with sqlite3.connect('games.db') as con:
        cur = con.cursor()
        cur.execute('''SELECT game_id, password, squares, x_is_next, x_goes_next, 
                    o_connected, score_for_x, score_for_o,
                    game_type, last_ping_response, messages FROM game''')
        for row in cur.fetchall():
            game = Game(row[8])
            game.game_id = row[0]
            game.password = json.loads(row[1])
            game.squares = json.loads(row[2])
            game.x_is_next = bool(row[3])
            game.x_goes_next = bool(row[4])
            game.o_connected = bool(row[5])
            game.score_for_x = row[6]
            game.score_for_o = row[7]
            game.last_ping_response = json.loads(row[9])
            game.messages = json.loads(row[10])
            games[game.game_id] = game


def assign_game_to_new_player(gameType):
    global games
    password = get_new_password()
    if gameType == "player_vs_player":
        with sqlite3.connect('games.db') as con:
            cur = con.cursor()
            cur.execute('SELECT game_id FROM game WHERE game_type="player_vs_player" and o_connected=0')
            row = cur.fetchone()
        if row is not None:
            game_id = row[0]
            games[game_id].assign_password('O', password)
            games[game_id].o_connected = True
            games[game_id].update_record_in_database()
            return games[game_id], 'O'

    game = Game(gameType)
    game.assign_password('X', password)
    game.save_new_game_to_database()
    games[game.game_id] = game
    return game, 'X'


def check_and_get_game():
    global games
    cookie_player = request.cookies.get('player_code')
    cookie_password = request.cookies.get('password')
    cookie_game_id = int(request.cookies.get('game_id', 0))
    cookie_game_type = request.cookies.get('game_type')

    if (cookie_player and cookie_game_id and
            cookie_game_id in games and
            cookie_game_type and
            games[cookie_game_id].password[cookie_player] == cookie_password and
            games[cookie_game_id].game_type == cookie_game_type):
        return games[cookie_game_id], cookie_player
    return None, None


def calculate_is_board_filled(squares):
    for sq in squares:
        if not sq:
            return False
    return True


def calculate_winner(squares):
    lines = [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7, 8],
        [0, 3, 6],
        [1, 4, 7],
        [2, 5, 8],
        [0, 4, 8],
        [2, 4, 6],
    ]
    for [a, b, c] in lines:
        if squares[a] and squares[a] == squares[b] and squares[a] == squares[c]:
            return squares[a]
    return None


def create_app(test_config=None):
    if os.path.exists('games.db'):
        load_games_from_database()
    else:
        with sqlite3.connect('games.db') as con:
            cur = con.cursor()
            cur.execute('''CREATE TABLE game(
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                password TEXT,
                squares TEXT,
                x_is_next INTEGER,
                x_goes_next INTEGER,
                o_connected INTEGER,
                score_for_x INTEGER,
                score_for_o INTEGER,
                game_type INTEGER,
                last_ping_response TEXT,
                messages TEXT
            )''')
            con.commit()

    app = Flask(__name__, static_url_path='', static_folder='.')
    @app.route("/")
    def hello_world():
        return redirect("/index.html")

    @app.route("/stream")
    def stream():
        gameType = request.args['game_type']
        assert gameType
        game, cookie_player = check_and_get_game()
        if game and cookie_player and game.game_type == gameType:
            player_code = cookie_player
        else:
            game, player_code = assign_game_to_new_player(gameType)

        def eventStream():
            while True:
                yield 'data: {}\n\n'.format(json.dumps({
                    'player_code': player_code,
                    'squares': game.squares,
                    'x_is_next': game.x_is_next,
                    'status': game.compute_status(),
                    'score': {'X': game.score_for_x, 'O': game.score_for_o},
                    'messages' : game.messages,
                }))
                if test_config and test_config.get('TESTING'):
                    break
                with game.condition:
                    game.condition.wait()

        respose = Response(eventStream(), mimetype="text/event-stream")
        respose.set_cookie('player_code', player_code)
        respose.set_cookie('password', game.password[player_code])
        respose.set_cookie('game_id', str(game.game_id))
        respose.set_cookie('game_type', gameType)
        return respose

    @app.route("/reset-game")
    def reset_game():
        game, _player = check_and_get_game()
        if game and game.compute_status()['is_restartable']:
            game.squares = [None] * 9
            game.x_is_next = game.x_goes_next
            game.x_goes_next = not game.x_goes_next
            if game.game_type == 'player_vs_computer' and not game.x_is_next:
                game.play_computer_move()
            game.update_record_in_database()
            with game.condition:
                game.condition.notify_all()
        return ''

    @app.route("/play-move")
    def play_move():
        move = int(request.args['move'])
        game, player = check_and_get_game()
        if (game and game.game_type=='two_players' and not game.x_is_next):
            player = 'O'
        player_is_x = player == 'X'
        if (game and player_is_x == game.x_is_next and
                game.squares[move] is None and
                not game.compute_status()['winning_player']):
            game.squares[move] = player
            game.x_is_next = not game.x_is_next
            game.update_score_new_move()
            if game.game_type == 'player_vs_computer':
                if not calculate_winner(game.squares):
                    game.play_computer_move()
                    game.update_score_new_move()
            game.update_record_in_database()
            with game.condition:
                game.condition.notify_all()
        return ''

    @app.route("/ping")
    def ping():
        game, player = check_and_get_game()
        if game:
            game.last_ping_response[player] = time.time()
            game.update_record_in_database()
            last_ping_response_time = min(game.last_ping_response.values())
            if game.game_type == 'player_vs_player':
                if not last_ping_response_time:
                    return {
                        "error_message": "Waiting for player"
                    }

                if time.time() - last_ping_response_time > 120:
                    return {
                        "error_message": "Player disconnected"
                    }

            return {
                "error_message": None
            }
        return {
            "error_message": "Invalid game"
        }

    @app.route("/api/new-message", methods=["POST"])
    def sendMessage():
        game, player = check_and_get_game()
        game.messages.append({"message":player+": "+request.json["newMessage"]})
        with game.condition:
            game.condition.notify_all()
        return jsonify(game.messages)

    return app


'''
TODO:
 - Add chat
 - Add more advanced database
 - Add cleanup of old games

MINOR changes:
 - add locking for all operations. a = threading.Lock()
 - /play-move /reset-game should be POST (not GET)

TODO cleanup:
 - reduce number of global variable
 - use class for better abstraction
 - use linter for python and javascript
 - compile javascript JXS in advance
'''
