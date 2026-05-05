from flask import Flask, send_from_directory, abort, jsonify
from flask_login import LoginManager
from config import Config
from models import db, Admin
from routes import routes
import os

SKY_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sky')

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Admin.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        return jsonify({'status': 'error', 'message': 'Authentication required.'}), 401
    app.register_blueprint(routes)
    @app.route('/')
    def index():
        return send_from_directory(SKY_FOLDER, 'admin.html')
    # Handles: /admin.css  /admin.js  /any-image.png etc.
    @app.route('/<path:filename>')
    def sky_static(filename):
        sky_path = os.path.join(SKY_FOLDER, filename)
        if os.path.exists(sky_path):
            return send_from_directory(SKY_FOLDER, filename)
        abort(404)
    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)