from flask import Flask, Response, redirect, request
import time
import json
import threading


app = Flask(__name__, static_url_path='', static_folder='.')

@app.route("/")
def hello_world():
	return redirect("/index.html")


next_player_is_x = 0
def get_player_code():
	global next_player_is_x
	if next_player_is_x:
		next_player_is_x = False
		return 'X'

	if not next_player_is_x:
		next_player_is_x = True
		return 'O'


squares = [None] * 9
x_is_next = True
x_goes_next = False
score_for_x = 0
score_for_o = 0
condition = threading.Condition()


@app.route("/play-move")
def play_move():
	global squares, x_is_next
	move = int(request.args['move'])
	player = request.args['player']
	player_is_x = player == 'X'
	if (player_is_x == x_is_next and
			squares[move] is None and
			not computeStatus()['winning_player']):
		squares[move] = player
		x_is_next = not x_is_next
		updateScoreNewMove()
		with condition:
			condition.notify_all()
	return ''

def updateScoreNewMove():
	winner = computeStatus()['winning_player']
	if winner == 'X':
		global score_for_x
		score_for_x += 1
	elif winner == 'O':
		global score_for_o
		score_for_o += 1


@app.route("/reset-game")
def reset_game():
	global squares, x_is_next, x_goes_next
	if computeStatus()['is_restartable']:
		squares = [None] * 9
		x_is_next = x_goes_next
		x_goes_next = not x_goes_next
		with condition:
			condition.notify_all()
	return ''


@app.route("/stream")
def stream():
	player_code = get_player_code()
	def eventStream():
		while True:
			yield 'data: {}\n\n'.format(json.dumps({
				'player_code': player_code,
				'squares': squares,
				'x_is_next': x_is_next,
				'status': computeStatus(),
				'score': {'X': score_for_x, 'O': score_for_o},
			}))
			with condition:
				condition.wait()

	return Response(eventStream(), mimetype="text/event-stream")



def calculateIsBoardFilled():
	for sq in squares:
		if not sq:
			return False
	return True


def calculateWinner():
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


def computeStatus():
	player = calculateWinner()
	winning_player = None
	if player:
		winning_player = player
		message = 'Winner ' + player
		is_restartable = True
	elif calculateIsBoardFilled():
		message = 'Nobody wins :('
		is_restartable = True
	else:
		message = 'Next player: ' + ('X' if x_is_next else 'O')
		is_restartable = False
	return {
		'winning_player': winning_player,
		'message': message,
		'is_restartable': is_restartable,
	}

'''
TODO:
 - keep score for players
 - multiple games
 - password per player per game
 - connection reset handling
 - choose local versus networked game
 - AI opponent, minimax search
 - add locking for all operations. a = threading.Lock()
 - /play-move /reset-game should be POST (not GET)

TODO cleanup:
 - reduce number of global variable
 - use class for better abstraction
'''
