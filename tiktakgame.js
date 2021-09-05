function Square(props){
  return (
    <button 
      className="square" 
      onClick={props.onClick}
    >
      {props.value}
    </button>
  );
}

function Board(props) {
  function renderSquare(i) {
    return <Square value={props.squares[i]} onClick={()=>props.onClick(i)} />;
  }

  return (
    <div>
      <div className="board-row">
        {renderSquare(0)}
        {renderSquare(1)}
        {renderSquare(2)}
      </div>
      <div className="board-row">
        {renderSquare(3)}
        {renderSquare(4)}
        {renderSquare(5)}
      </div>
      <div className="board-row">
        {renderSquare(6)}
        {renderSquare(7)}
        {renderSquare(8)}
      </div>
    </div>
  );
}

function Game(props) {
  var [playerCode, setPlayerCode] = React.useState(false);
  var [squares, setSquares] = React.useState(Array(9).fill(null));
  var [xIsNext, setXIsNext] = React.useState(true);

  React.useEffect(() => {
    var eventSource = new EventSource("/stream");
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setPlayerCode(data.player_code);
      setSquares(data.squares);
      setXIsNext(data.x_is_next);
    };
    return () => eventSource.close();
  }, []);

  function handleClick(i){
    if (calculateWinner(squares) || squares[i]){
      return;
    }
    fetch('/play-move?player=' + playerCode + '&move=' + i)
  }

  const winner = calculateWinner(squares);

  let status;
  if (winner) {
    status = 'Winner ' + winner;
  } else if (calculateIsDraw(squares)) {
    status = 'Nobody wins :(';
  } else {
    status = 'Next player: ' + (xIsNext ? 'X' : 'O');
  }

  if (!playerCode) {
    return (
      <div className="game">
        <p>Waiting on the server...</p>
      </div>
    )
  }

  return (
    <div className="game">
      <div className="game-board">
        <Board
          squares={squares}
          onClick={i => handleClick(i)}
        />
      </div>
      <div className="game-info">
        <div>You are: {playerCode}</div>
        <div>{status}</div>
      </div>
    </div>
  );
}

function calculateIsDraw(squares) {
  for (let i=0; i<squares.length; i++){
    if (!squares[i]) {
      return false;
    }
  }
  return true;
}

function calculateWinner(squares) {
  const lines = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],
    [0, 3, 6],
    [1, 4, 7],
    [2, 5, 8],
    [0, 4, 8],
    [2, 4, 6],
  ];
  for (let i=0; i<lines.length; i++){
    const [a,b,c] = lines[i];
    if (squares[a] && squares[a]===squares[b] && squares[a]===squares[c]) {
      return squares[a];
    }
  }
  return null;
}

ReactDOM.render(
  <Game />,
  document.getElementById('root')
);
