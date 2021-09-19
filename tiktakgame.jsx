const SymbolsContext = React.createContext({});

function Square(props){
  const symbols = React.useContext(SymbolsContext);
  return (
    <button 
      className="square" 
      onClick={props.onClick}
    >
      {props.value ? symbols[props.value] : ''}
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

function getCookie(cookiename) 
{
  // Get name followed by anything except a semicolon
  var cookiestring=RegExp(cookiename+"=[^;]+").exec(document.cookie);
  // Return everything after the equal sign, or an empty string if the cookie name not found
  return decodeURIComponent(!!cookiestring ? cookiestring.toString().replace(/^[^=]+./,"") : "");
}


function Game(props) {
  var [playerCode, setPlayerCode] = React.useState(false);
  var [squares, setSquares] = React.useState(Array(9).fill(null));
  var [xIsNext, setXIsNext] = React.useState(true);
  var [status, setStatus] = React.useState({});
  var [score, setScore] = React.useState({});

  React.useEffect(
    () => {
      var eventSource = new EventSource("/stream?game_type="+props.gameType);
      eventSource.onmessage = (e) => {
        const data = JSON.parse(e.data);
        setPlayerCode(data.player_code);
        setSquares(data.squares);
        setXIsNext(data.x_is_next);
        setStatus(data.status);
        setScore(data.score);
      };
      return () => eventSource.close();
    },
    []
  );
  const symbols = React.useContext(SymbolsContext);

  function handleClick(i){
    if (status.winning_player || squares[i]){
      return;
    }
    // TODO: use encodeURI or encodeURIComponent
    fetch('/play-move?move=' + i)
      .then(r => null, e => console.log(e));
  }

  function handleReset() {
    fetch('/reset-game')
      .then(r => null, e => console.log(e));
  }

  if (!playerCode) {
    return (
      <div className="game">
        <p>Waiting on the server...</p>
      </div>
    )
  }

  let reset_button = <React.Fragment />;
  let message;
  if (status.is_restartable) {
    reset_button = <input type="button" value="Reset" onClick={() => handleReset()} ></input>;
    if (status.winning_player) {
      message = 'Winner ' + symbols[status.winning_player];
    } else {
      message = 'Nobody wins :(';
    }
  } else {
    message = 'Next player: ' + symbols[xIsNext ? 'X' : 'O'];
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
        <div>{props.gameType}</div>
        <div>You are: {symbols[playerCode]}</div>
        <div>{message}</div>
        <hr />
        <div>{symbols['X']} vs {symbols['O']}</div>
        <div>{score.X} : {score.O}</div>
        {reset_button}
        <input type="button" value="Change game type" onClick={props.changeGameTypeCallback} ></input>
      </div>
    </div>
  );
}

function GameSelection(props) {
  var [gameType, setGameType] = React.useState("");
  React.useEffect(
    () => {
      var cookieGameType = getCookie('game_type');
      if(cookieGameType) setGameType(cookieGameType);
    },
    []
  );
  if(gameType===""){
    return(
      <div>
        <h2>Choose game type:</h2>
        <button onClick={() => setGameType("player_vs_computer")}>Player vs Computer</button>
        <button onClick={() => setGameType("player_vs_player")}>Player vs Player</button>
      </div>
    );
  }else{
    return(
      <div>
        <SymbolsContext.Provider value={{'X': '❌', 'O': '⭕'}}>
          <Game gameType={gameType} changeGameTypeCallback={() => setGameType("")} />
        </SymbolsContext.Provider>
      </div>
    );
  }
}

ReactDOM.render(
  <GameSelection />,
  document.getElementById('root')
);
