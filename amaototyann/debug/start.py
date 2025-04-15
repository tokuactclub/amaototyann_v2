import threading
from amaototyann.debug.debugger import app as debug_app
from amaototyann.src.server import app as server_app

def run_debug_app():
    debug_app.run(debug=True, port=10000, use_reloader=False)

def run_server_app():
    server_app.run(debug=True, port=8000, use_reloader=False)

if __name__ == "__main__":
    debug_thread = threading.Thread(target=run_debug_app)
    server_thread = threading.Thread(target=run_server_app)

    debug_thread.start()
    server_thread.start()

    debug_thread.join()
    server_thread.join()
