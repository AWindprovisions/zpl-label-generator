import os
import sys
import time

from flask import Flask, send_from_directory, redirect, request
from flask_cors import CORS

# Import the zpl_processor blueprint
try:
    from routes.zpl_processor import zpl_bp
    from routes.auth import auth_bp
except ImportError:
    from src.routes.zpl_processor import zpl_bp
    from src.routes.auth import auth_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'prod_flask_secret_2024_' + str(int(time.time())))

# Enable CORS for all routes
CORS(app)

app.register_blueprint(zpl_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')

@app.route('/')
def index():
    """Página inicial - redireciona para login"""
    return send_from_directory(app.static_folder, 'login.html')

@app.route('/app')
def app_page():
    """Página do aplicativo - requer autenticação"""
    return send_from_directory(app.static_folder, 'app.html')

@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        # Redirecionar para login se arquivo não encontrado
        return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=False)
