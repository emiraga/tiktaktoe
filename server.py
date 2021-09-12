from flask import Flask, Response, redirect, request
import json
import threading
import random
import string


last_game_id = 0
games = {}


def get_new_password():
	return ''.join(random.choice(string.ascii_uppercase) for _ in range(10))


def assign_game_to_new_player():
	global last_game_id
	global games
	if not last_game_id or not games[last_game_id]['single_player']:
		last_game_id+=1
		games[last_game_id]={
			'password' : {'X': None, 'O': None},
			'squares' : [None] * 9,
			'x_is_next' : True,
			'x_goes_next' : False,
			'score_for_x' : 0,
			'score_for_o' : 0,
			'condition' : threading.Condition(),
			'single_player': True,
		}
		return last_game_id,'X'
	else:
		games[last_game_id]['single_player']=False
		return last_game_id,'O'


def check_password_for_player():
	cookie_player = request.cookies.get('player_code')
	cookie_password = request.cookies.get('password')
	cookie_game_id = int(request.cookies.get('game_id', 0))
	if (cookie_player and cookie_game_id and
		cookie_game_id in games and
		games[cookie_game_id]['password'][cookie_player] == cookie_password):
			return True
	return False


def updateScoreNewMove(game_id):
	global games
	winner = computeStatus(game_id)['winning_player']
	if winner == 'X':
		games[game_id]['score_for_x'] += 1
	elif winner == 'O':
		games[game_id]['score_for_o'] += 1


def calculateIsBoardFilled(squares):
	for sq in squares:
		if not sq:
			return False
	return True


def calculateWinner(squares):
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
	for [a,b,c] in lines:	
		if squares[a] and squares[a] == squares[b] and squares[a] == squares[c]:
			return squares[a]
	return None


def computeStatus(game_id):
	player = calculateWinner(games[game_id]['squares'])
	winning_player = None
	if player:
		winning_player = player
		message = 'Winner ' + player
		is_restartable = True
	elif calculateIsBoardFilled(games[game_id]['squares']):
		message = 'Nobody wins :('
		is_restartable = True
	else:
		message = 'Next player: ' + ('X' if games[game_id]['x_is_next'] else 'O')
		is_restartable = False
	return {
		'winning_player': winning_player,
		'message': message,
		'is_restartable': is_restartable,
	}


def create_app(test_config=None):
	app = Flask(__name__, static_url_path='', static_folder='.')
	@app.route("/")
	def hello_world():
		return redirect("/index.html")

	@app.route("/stream")
	def stream():
		cookie_player = request.cookies.get('player_code')
		cookie_password = request.cookies.get('password')
		cookie_game_id = int(request.cookies.get('game_id', 0))
		global games
		if cookie_player and cookie_game_id and cookie_game_id in games and games[cookie_game_id]['password'][cookie_player] == cookie_password:
			# Reuse existing password
			game_id=cookie_game_id
			player_code = cookie_player
			player_password = cookie_password
		else:
			# Generate new code and password
			game_id, player_code = assign_game_to_new_player()
			player_password = get_new_password()
			games[game_id]['password'][player_code] = player_password

		def eventStream():
			while True:
				yield 'data: {}\n\n'.format(json.dumps({
					'player_code': player_code,
					'squares': games[game_id]['squares'],
					'x_is_next': games[game_id]['x_is_next'],
					'status': computeStatus(game_id),
					'score': {'X': games[game_id]['score_for_x'], 'O': games[game_id]['score_for_o']},
				}))
				if test_config and test_config.get('TESTING'):
					break
				with games[game_id]['condition']:
					games[game_id]['condition'].wait()

		respose = Response(eventStream(), mimetype="text/event-stream")
		respose.set_cookie('player_code', player_code)
		respose.set_cookie('password', player_password)
		respose.set_cookie('game_id', str(game_id))
		return respose

	@app.route("/reset-game")
	def reset_game():
		global games
		game_id = int(request.cookies.get('game_id', 0))
		if not check_password_for_player():
			raise Exception('Wrong password')

		if computeStatus(game_id)['is_restartable']:
			games[game_id]['squares'] = [None] * 9
			games[game_id]['x_is_next'] = games[game_id]['x_goes_next']
			games[game_id]['x_goes_next'] = not games[game_id]['x_goes_next']
			with games[game_id]['condition']:
				games[game_id]['condition'].notify_all()
		return ''

	@app.route("/play-move")
	def play_move():
		global games
		game_id = int(request.cookies.get('game_id', 0))
		move = int(request.args['move'])
		player = request.cookies['player_code']
		if not check_password_for_player():
			raise Exception('Wrong password for player ' + player)
		player_is_x = player == 'X'
		if (player_is_x == games[game_id]['x_is_next'] and
				games[game_id]['squares'][move] is None and
				not computeStatus(game_id)['winning_player']):
			games[game_id]['squares'][move] = player
			games[game_id]['x_is_next'] = not games[game_id]['x_is_next']
			updateScoreNewMove(game_id)
			with games[game_id]['condition']:
				games[game_id]['condition'].notify_all()
		return ''

	return app


'''
TODO:
 - choose local versus networked game
 - AI opponent, minimax search
 - Automatic Testing

MINOR changes:
 - add locking for all operations. a = threading.Lock()
 - /play-move /reset-game should be POST (not GET)

TODO cleanup:
 - reduce number of global variable
 - use class for better abstraction
'''
