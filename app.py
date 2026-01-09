from flask import Flask, render_template, request, Response, send_file
from flask_socketio import SocketIO, emit
from threading import Thread
import time
import os
import logging
from game_engine import GameState, ai_make_move

# --- Logging Setup ---
history_logger = logging.getLogger('game_history')
history_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('game_history.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
history_logger.addHandler(file_handler)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pro-battle-token-secret'
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

LOG_FILE = "chat_records.log"
ADMIN_KEY = "admin123"

# 初始化遊戲狀態
game = GameState()

def save_to_file(entry: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception as e:
        print(f"寫入檔案失敗: {e}")

def broadcast_update():
    winner = game.check_winner() if game.game_active else None
    next_f = None
    if game.game_active and not game.paused:
        moves = game.x_moves if game.current_turn == "X" else game.o_moves
        if len(moves) >= game.MAX_PIECES:
            next_f = moves[0]

    socketio.emit('update_board', {
        'board': game.board,
        'next_turn': game.current_turn,
        'winner': winner,
        'next_to_fade': next_f,
        'players': game.players,
        'scores': game.scores,
        'queue': game.queue,
        'game_active': game.game_active,
        'paused': game.paused
    })

def handle_game_end(winner):
    """處理遊戲結束的共用邏輯"""
    duration = round(time.time() - game.game_start_time, 2)
    winner_type = "(AI)" if game.ai_enabled[winner] else ""
    log_message = (
        f"Result: {winner} {winner_type} Wins | "
        f"Total Turns: {game.total_moves} | "
        f"Duration: {duration}s"
    )
    history_logger.info(log_message)

    game.game_active = False
    game.scores[winner] += 1
    broadcast_update()
    socketio.emit('game_winner', {'winner': winner, 'winner_name': game.players[winner]})

    def auto_reset():
        time.sleep(2)
        with app.app_context():
            game.reset()
            broadcast_update()
    Thread(target=auto_reset, daemon=True).start()

def timeout_monitor():
    while True:
        time.sleep(0.1)
        if game.game_active and not game.paused and game.players["X"] and game.players["O"]:
            # --- AI 邏輯 ---
            if game.ai_enabled[game.current_turn]:
                idx = ai_make_move(game) # 傳入 game 實體
                if idx is not None:
                    moves = game.x_moves if game.current_turn == "X" else game.o_moves
                    if len(moves) >= game.MAX_PIECES:
                        game.board[moves.pop(0)] = ""
                    moves.append(idx)
                    game.board[idx] = game.current_turn
                    game.total_moves += 1

                    winner = game.check_winner()
                    if winner:
                        handle_game_end(winner)
                    else:
                        game.current_turn = "O" if game.current_turn == "X" else "X"
                        game.turn_start_time = time.time()
                        broadcast_update()

            # --- 人類超時邏輯 ---
            elif time.time() - game.turn_start_time > game.TURN_TIMEOUT:
                role = game.current_turn
                sid = game.player_sids.get(role)
                if sid and not game.ai_enabled[role]:
                    socketio.emit('sys_notif', {'msg': f'玩家 {role} 回合超時！'})
                    game.remove_player(sid)
                    game.reset()
                    new_p = game.promote_from_queue(role)
                    if new_p:
                        socketio.emit('promoted_to_player', {
                            'role': role, 'board': game.board, 'players': game.players,
                            'scores': game.scores, 'queue': game.queue, 'next_turn': game.current_turn
                        }, room=new_p['sid'])
                    else:
                        if role == "O": game.enable_ai("O")
                    broadcast_update()

Thread(target=timeout_monitor, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

# --- Admin Routes ---
@app.route('/admin/logs')
def admin_dashboard():
    key = request.args.get('key')
    if key != ADMIN_KEY: return Response("Access Denied", status=403)
    log_files = {"game_history": "game_history.log", "chat_records": "chat_records.log"}
    html = "<h1>Admin Log Dashboard</h1><ul>"
    for name, filename in log_files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename) / 1024
            html += f'<li><a href="/admin/download/{filename}?key={ADMIN_KEY}">{filename}</a> ({size:.2f} KB)</li>'
        else:
            html += f'<li>{filename} (尚無檔案)</li>'
    html += "</ul>"
    return html

@app.route('/admin/download/<filename>')
def download_log(filename):
    key = request.args.get('key')
    if key != ADMIN_KEY: return Response("Access Denied", status=403)
    if filename not in ["game_history.log", "chat_records.log"]: return Response("File not allowed", status=403)
    if not os.path.exists(filename): return Response("File not found", status=404)
    return send_file(filename, as_attachment=True, download_name=f"{filename.split('.')[0]}_{time.strftime('%Y%m%d_%H%M%S')}.txt", mimetype='text/plain')

# --- Socket Events ---
@app.route('/admin/export10380045_logs') # 保留舊路由以防萬一，或可刪除
def export_logs(): return Response("Old route. Use /admin/logs", mimetype="text/plain")

@socketio.on('join_game')
def handle_join(data):
    name, sid = data.get('name', '匿名')[:12], request.sid
    role = "Observer"
    existing_roles = [r for r in ["X", "O"] if game.players[r] and not game.ai_enabled[r]]

    if not game.players["X"] or game.ai_enabled["X"]:
        game.disable_ai("X")
        game.players["X"], game.player_sids["X"], role = name, sid, "X"
        game.ai_enabled["X"] = False
        if not game.players["O"] or game.ai_enabled["O"]: game.enable_ai("O")
    elif not game.players["O"] or game.ai_enabled["O"]:
        game.disable_ai("O")
        game.players["O"], game.player_sids["O"], role = name, sid, "O"
        game.ai_enabled["O"] = False
    else:
        if len(game.queue) >= game.MAX_QUEUE:
            emit('sys_notif', {'msg': '排隊人數已達上限！'})
            return
        game.queue.append({'sid': sid, 'name': name})

    emit('assign_role', {'role': role, 'board': game.board, 'players': game.players, 'scores': game.scores, 'queue': game.queue, 'next_turn': game.current_turn})
    broadcast_update()
    if role != "Observer" and len(existing_roles) == 0:
        game.reset()
        broadcast_update()

@socketio.on('make_move')
def handle_move(data):
    if game.paused: return
    idx, sid = data.get('index'), request.sid
    if sid != game.player_sids.get(game.current_turn): return
    if game.board[idx] != "": return

    moves = game.x_moves if game.current_turn == "X" else game.o_moves
    if len(moves) >= game.MAX_PIECES: game.board[moves.pop(0)] = ""
    moves.append(idx)
    game.board[idx] = game.current_turn
    game.total_moves += 1

    winner = game.check_winner()
    if winner:
        handle_game_end(winner)
    else:
        game.current_turn = "O" if game.current_turn == "X" else "X"
        game.turn_start_time = time.time()
        broadcast_update()

@socketio.on('toggle_pause')
def handle_pause():
    sid = request.sid
    if sid not in game.player_sids.values(): return
    if not game.paused:
        game.paused, game.pause_start_time = True, time.time()
    else:
        game.turn_start_time += (time.time() - game.pause_start_time)
        game.paused = False
    broadcast_update()

@socketio.on('disconnect')
def handle_disconnect():
    role = game.remove_player(request.sid)
    if role:
        game.reset()
        new_p = game.promote_from_queue(role)
        if new_p:
            socketio.emit('promoted_to_player', {'role': role, 'board': game.board, 'players': game.players, 'scores': game.scores, 'queue': game.queue, 'next_turn': game.current_turn}, room=new_p['sid'])
        else:
            if role == "O": game.enable_ai("O")
        broadcast_update()

@socketio.on('reset_game')
def handle_reset():
    game.reset()
    broadcast_update()

@socketio.on('kick_opponent')
def handle_kick():
    sid = request.sid
    role = "X" if game.player_sids["X"] == sid else ("O" if game.player_sids["O"] == sid else None)
    if role:
        opp = "O" if role == "X" else "X"
        old_sid = game.player_sids[opp]
        if game.ai_enabled[opp]:
            socketio.emit('sys_notif', {'msg': '無法踢除 AI 玩家！'}, room=sid)
            return
        game.players[opp], game.player_sids[opp] = None, None
        new_p = game.promote_from_queue(opp)
        if old_sid: socketio.emit('kicked_by_opponent', {'message': '換人玩囉！'}, room=old_sid)
        if new_p:
            socketio.emit('promoted_to_player', {'role': opp, 'board': game.board, 'players': game.players, 'scores': game.scores, 'queue': game.queue, 'next_turn': game.current_turn}, room=new_p['sid'])
        else:
            if opp == "O": game.enable_ai("O")
        game.reset()
        broadcast_update()

@socketio.on('send_message')
def handle_msg(data):
    sid = request.sid
    message = data.get('message', '')[:100]
    sender_name = "訪客"
    for r in ["X", "O"]:
        if game.player_sids[r] == sid:
            sender_name = game.players[r]
            break
    if sender_name == "訪客":
        for p in game.queue:
            if p['sid'] == sid:
                sender_name = p['name']
                break
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    save_to_file(f"[{timestamp}] {sender_name}: {message}")
    socketio.emit('new_message', {'sender': sender_name, 'message': message})

@socketio.on('heartbeat')
def handle_heartbeat():
    rem = max(0, int(game.TURN_TIMEOUT - ((time.time() - game.pause_start_time) if game.paused else (time.time() - game.turn_start_time))))
    emit('heartbeat_response', {'remaining_time': rem})

@socketio.on('set_ai_difficulty')
def handle_set_difficulty(data):
    difficulty = data.get('difficulty', 'medium')
    if difficulty in ['easy', 'medium', 'hard']:
        game.ai_difficulty = difficulty
        socketio.emit('new_message', {'sender': '系統', 'message': f'AI 難度已設定為: {difficulty}'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080)