import json
import threading
import random
import string
from flask import Flask, Response, redirect, request

games = {}
last_single_player_id = 0
last_game_id = 0


class Game:
    def __init__(self, game_id, game_type):
        self.password = {'X': None, 'O': None}
        self.squares = [None] * 9
        self.x_is_next = True
        self.x_goes_next = False
        self.score_for_x = 0
        self.score_for_o = 0
        self.condition = threading.Condition()
        self.game_type = game_type
        self.game_id = game_id

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


def compute_best_move(squares):
    for i in range(9):
        if not squares[i]:
            return i


def get_new_password():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(10))


def assign_game_to_new_player(gameType):
    global last_single_player_id
    global last_game_id
    global games
    password = get_new_password()
    if gameType == "player_vs_computer":
        last_game_id += 1
        games[last_game_id] = Game(last_game_id, gameType)
        games[last_game_id].assign_password('X', password)
        return games[last_game_id], 'X'

    if not last_single_player_id:
        last_game_id += 1
        last_single_player_id = last_game_id
        games[last_game_id] = Game(last_game_id, gameType)
        games[last_game_id].assign_password('X', password)
        return games[last_game_id], 'X'

    game_id = last_single_player_id
    last_single_player_id = 0
    games[game_id].assign_password('O', password)
    return games[game_id], 'O'


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
            with game.condition:
                game.condition.notify_all()
        return ''

    @app.route("/play-move")
    def play_move():
        move = int(request.args['move'])
        game, player = check_and_get_game()
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
            with game.condition:
                game.condition.notify_all()
        return ''

    return app


'''
TODO:
 - choose local versus networked game
 - AI opponent, minimax search
 - Automatic Testing
 - Periodic ping

MINOR changes:
 - add locking for all operations. a = threading.Lock()
 - /play-move /reset-game should be POST (not GET)

TODO cleanup:
 - reduce number of global variable
 - use class for better abstraction
 - use linter for python and javascript
 - compile javascript JXS in advance
'''
