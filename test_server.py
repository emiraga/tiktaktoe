import pytest
import json
from server import create_app


@pytest.fixture
def client():
    app = create_app({'TESTING': True})
    with app.test_client() as client:
        yield client
client1 = client
client2 = client
client3 = client


def test_root_response(client):
    rv = client.get('/')
    assert rv.headers.get('Location') == 'http://localhost/index.html'


def test_stream_connection_break_and_reconnect(client):
    rv = client.get('/stream?game_type=player_vs_player')
    cookie1 = rv.headers.get_all('Set-Cookie')

    rv = client.get('/stream?game_type=player_vs_player')
    cookie2 = rv.headers.get_all('Set-Cookie')
    assert cookie1 == cookie2

    client.delete_cookie(key='password', server_name='localhost')

    rv = client.get('/stream?game_type=player_vs_player')
    cookie3 = rv.headers.get_all('Set-Cookie')
    assert cookie1 != cookie3 and cookie2 != cookie3


def extract_cookie(response, search_name):
    for x in response.headers.get_all('Set-Cookie'):
        name, value = x.split(';')[0].split('=')
        if search_name == name:
            return value


def extract_json(response):
    data = response.get_data(as_text=True)
    assert data.startswith('data: ')
    return json.loads(data[6:])


def test_two_players_connecting(client1, client2):
    rv1 = client1.get('/stream?game_type=player_vs_player')
    rv2 = client2.get('/stream?game_type=player_vs_player')
    assert extract_cookie(rv1, 'game_id') == extract_cookie(rv2, 'game_id')
    assert extract_cookie(rv1, 'player_code') != extract_cookie(rv2, 'player_code')

    assert extract_json(rv1)['squares'] == [None] * 9
    rv1 = client1.get('/play-move?move=0')
    rv2 = client2.get('/stream?game_type=player_vs_player')
    assert extract_json(rv2)['squares'][0] == 'X'

def test_single_player_and_multiplayer(client1,client2,client3):
    rv1 = client1.get('/stream?game_type=player_vs_player')
    rv2 = client2.get('/stream?game_type=player_vs_computer')
    rv3 = client3.get('/stream?game_type=player_vs_player')

    assert extract_cookie(rv1, 'game_id') == extract_cookie(rv3, 'game_id')
    assert extract_cookie(rv1, 'game_id') != extract_cookie(rv2, 'game_id')