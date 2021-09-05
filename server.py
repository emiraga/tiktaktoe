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
condition = threading.Condition()


@app.route("/play-move")
def play_move():
	global squares
	global x_is_next
	move = int(request.args['move'])
	player = request.args['player']
	player_is_x = player == 'X'
	if player_is_x == x_is_next and squares[move] is None:
		squares[move] = player
		x_is_next = not x_is_next
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
			}))
			with condition:
				condition.wait()

	return Response(eventStream(), mimetype="text/event-stream")
