import eventlet  # <--- 新增這一行
import time
import random
import logging
from dataclasses import dataclass, field
from typing import List, Tuple

# --- Logging Setup (保持與 app.py 一致的 Log 邏輯，但這裡主要用於類別內) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GameEngine")


@dataclass
class GameState:
    """遊戲狀態管理中心"""
    board: List[str] = field(default_factory=lambda: [""] * 9)
    current_turn: str = "X"
    game_active: bool = True
    paused: bool = False
    x_moves: List[int] = field(default_factory=list)
    o_moves: List[int] = field(default_factory=list)
    players: dict = field(default_factory=lambda: {"X": None, "O": None})
    player_sids: dict = field(default_factory=lambda: {"X": None, "O": None})
    scores: dict = field(default_factory=lambda: {"X": 0, "O": 0})
    queue: List[dict] = field(default_factory=list)
    ai_enabled: dict = field(default_factory=lambda: {"X": False, "O": False})
    ai_difficulty: str = "medium"
    game_start_time: float = 0.0
    total_moves: int = 0

    turn_start_time: float = field(default_factory=time.time)
    pause_start_time: float = 0.0
    TURN_TIMEOUT: int = 30
    MAX_PIECES: int = 3
    MAX_QUEUE: int = 15

    WINNING_LINES: Tuple[Tuple[int, int, int], ...] = (
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6)
    )

    def __post_init__(self):
        self.game_start_time = time.time()

    def check_winner(self):
        for i, j, k in self.WINNING_LINES:
            if self.board[i] == self.board[j] == self.board[k] != "":
                return self.board[i]
        return None

    def reset(self):
        self.board = [""] * 9
        self.x_moves.clear()
        self.o_moves.clear()
        self.current_turn = "X"
        self.game_active = True
        self.paused = False
        self.turn_start_time = time.time()
        self.game_start_time = time.time()
        self.total_moves = 0
        print("Game state reset. Timer and move counter restarted.")

    def remove_player(self, sid: str):
        for role in ["X", "O"]:
            if self.player_sids[role] == sid:
                self.players[role] = None
                self.player_sids[role] = None
                self.ai_enabled[role] = False
                return role
        self.queue = [p for p in self.queue if p['sid'] != sid]
        return None

    def promote_from_queue(self, role: str):
        if self.queue:
            next_p = self.queue.pop(0)
            self.players[role] = next_p['name']
            self.player_sids[role] = next_p['sid']
            self.ai_enabled[role] = False
            return next_p
        return None

    def enable_ai(self, role: str):
        self.players[role] = f"🤖 AI {role}"
        self.player_sids[role] = f"AI_{role}"
        self.ai_enabled[role] = True

    def disable_ai(self, role: str):
        if self.ai_enabled[role]:
            self.players[role] = None
            self.player_sids[role] = None
            self.ai_enabled[role] = False


# --- AI Helper Functions ---

def check_winner_on_board(board):
    winning_lines = (
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6)
    )
    for i, j, k in winning_lines:
        if board[i] == board[j] == board[k] != "":
            return board[i]
    return None


def simulate_move(board, x_moves, o_moves, move_idx, player):
    new_board = board.copy()
    new_x_moves = x_moves.copy()
    new_o_moves = o_moves.copy()

    moves = new_x_moves if player == "X" else new_o_moves
    if len(moves) >= 3:
        removed_idx = moves.pop(0)
        new_board[removed_idx] = ""

    moves.append(move_idx)
    new_board[move_idx] = player
    return new_board, new_x_moves, new_o_moves


def minimax_infinite(board, x_moves, o_moves, depth, is_maximizing, role, opponent, alpha=-float('inf'),
                     beta=float('inf')):
    eventlet.sleep(0)  # <--- 【關鍵修改】讓伺服器換氣，防止斷線！
    winner = check_winner_on_board(board)
    if winner == role:
        return 100 - depth
    elif winner == opponent:
        return depth - 100
    elif "" not in board:
        return 0
    if depth >= 2: return 0  # 稍微降低深度以優化效能

    empty = [i for i in range(9) if board[i] == ""]

    if is_maximizing:
        max_eval = -float('inf')
        for i in empty:
            nb, nx, no = simulate_move(board, x_moves, o_moves, i, role)
            eval_score = minimax_infinite(nb, nx, no, depth + 1, False, role, opponent, alpha, beta)
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha: break
        return max_eval
    else:
        min_eval = float('inf')
        for i in empty:
            nb, nx, no = simulate_move(board, x_moves, o_moves, i, opponent)
            eval_score = minimax_infinite(nb, nx, no, depth + 1, True, role, opponent, alpha, beta)
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha: break
        return min_eval


def find_fork(board, x_moves, o_moves, player):
    fork_positions = []
    empty = [i for i in range(9) if board[i] == ""]
    for i in empty:
        tb, tx, to = simulate_move(board, x_moves, o_moves, i, player)
        winning_moves = 0
        te = [j for j in range(9) if tb[j] == ""]
        for j in te:
            tb2, _, _ = simulate_move(tb, tx, to, j, player)
            if check_winner_on_board(tb2) == player:
                winning_moves += 1
        if winning_moves >= 2:
            fork_positions.append(i)
    return fork_positions


def basic_strategy(game: GameState, role, opponent, empty):
    # 傳入 game 物件以獲取當前棋盤
    board = game.board
    x_moves = game.x_moves
    o_moves = game.o_moves

    for i in empty:
        tb, _, _ = simulate_move(board, x_moves, o_moves, i, role)
        if check_winner_on_board(tb) == role: return i
    for i in empty:
        tb, _, _ = simulate_move(board, x_moves, o_moves, i, opponent)
        if check_winner_on_board(tb) == opponent: return i
    if 4 in empty: return 4
    corners = [c for c in [0, 2, 6, 8] if c in empty]
    if corners: return random.choice(corners)
    return random.choice(empty)


def advanced_strategy(game: GameState, role, opponent, empty):
    board = game.board
    x_moves = game.x_moves
    o_moves = game.o_moves

    for i in empty:
        tb, _, _ = simulate_move(board, x_moves, o_moves, i, role)
        if check_winner_on_board(tb) == role: return i
    for i in empty:
        tb, _, _ = simulate_move(board, x_moves, o_moves, i, opponent)
        if check_winner_on_board(tb) == opponent: return i

    my_forks = find_fork(board, x_moves, o_moves, role)
    if my_forks: return random.choice(my_forks)

    opp_forks = find_fork(board, x_moves, o_moves, opponent)
    if opp_forks:
        for i in empty:
            tb, tx, to = simulate_move(board, x_moves, o_moves, i, role)
            te = [j for j in range(9) if tb[j] == ""]
            for j in te:
                tb2, _, _ = simulate_move(tb, tx, to, j, role)
                if check_winner_on_board(tb2) == role: return i
        return random.choice(opp_forks)

    if 4 in empty: return 4
    corners = [c for c in [0, 2, 6, 8] if c in empty]
    if corners: return random.choice(corners)
    edges = [e for e in [1, 3, 5, 7] if e in empty]
    if edges: return random.choice(edges)
    return random.choice(empty)


def ai_make_move(game: GameState):
    """AI 下棋邏輯介面"""
    if not game.game_active or game.paused: return None
    role = game.current_turn
    if not game.ai_enabled[role]: return None

    #time.sleep(0.3)

    board = game.board.copy()
    x_moves = game.x_moves.copy()
    o_moves = game.o_moves.copy()
    empty = [i for i in range(9) if board[i] == ""]
    if not empty: return None

    opponent = "O" if role == "X" else "X"

    if game.ai_difficulty == "easy":
        if random.random() < 0.5: return random.choice(empty)
        return basic_strategy(game, role, opponent, empty)

    elif game.ai_difficulty == "medium":
        if random.random() < 0.2: return random.choice(empty)
        return advanced_strategy(game, role, opponent, empty)

    elif game.ai_difficulty == "hard":
        best_score = -float('inf')
        best_move = None
        for i in empty:
            tb, tx, to = simulate_move(board, x_moves, o_moves, i, role)
            score = minimax_infinite(tb, tx, to, 0, False, role, opponent)
            if score > best_score:
                best_score = score
                best_move = i
        return best_move if best_move is not None else random.choice(empty)

    return random.choice(empty)