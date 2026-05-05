import secrets
from datetime import datetime, timedelta
from sqlalchemy import func
from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Admin, Opportunity, PasswordResetToken

routes = Blueprint('routes', __name__)

ALLOWED_CATEGORIES = {'Technology', 'Business', 'Design', 'Marketing', 'Data Science', 'Other'}

def json_error(msg, code=400):
    return jsonify({'status': 'error', 'message': msg}), code

def json_ok(data=None, msg='Success', code=200):
    resp = {'status': 'success', 'message': msg}
    if data is not None:
        resp['data'] = data
    return jsonify(resp), code
@routes.route('/api/signup', methods=['POST'])
def signup():
    body = request.get_json(silent=True) or {}

    full_name        = (body.get('full_name') or '').strip()
    email            = (body.get('email') or '').strip().lower()
    password         = body.get('password', '')
    confirm_password = body.get('confirm_password', '')

    # --- Validations ---
    if not all([full_name, email, password, confirm_password]):
        return json_error('All fields are required.')
    if '@' not in email or '.' not in email.split('@')[-1]:
        return json_error('Enter a valid email address.')
    if len(password) < 8:
        return json_error('Password must be at least 8 characters.')
    if password != confirm_password:
        return json_error('Passwords do not match.')
    if Admin.query.filter_by(email=email).first():
        return json_error('This email is already registered.')

    # --- Save ---
    admin = Admin(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(admin)
    db.session.commit()

    return json_ok(msg='Account created successfully.', code=201)
@routes.route('/api/login', methods=['POST'])
def login():
    body = request.get_json(silent=True) or {}

    email       = (body.get('email') or '').strip().lower()
    password    = body.get('password', '')
    remember_me = bool(body.get('remember_me', False))

    admin = Admin.query.filter_by(email=email).first()

    if not admin or not check_password_hash(admin.password_hash, password):
        return json_error('Invalid email or password.', 401)

    login_user(admin, remember=remember_me)

    return json_ok(
        data={'admin': admin.to_dict()},
        msg='Login successful.'
    )
@routes.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    body  = request.get_json(silent=True) or {}
    email = (body.get('email') or '').strip().lower()

    admin = Admin.query.filter(func.lower(Admin.email) == email).first()

    if admin:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        reset = PasswordResetToken(
            admin_id=admin.id,
            token=token,
            expires_at=expires_at
        )
        db.session.add(reset)
        db.session.commit()

        # Required by assignment: log link instead of emailing
        reset_link = f'http://localhost:5000/api/reset-password/{token}'
        print(f'\n[PASSWORD RESET LINK] {reset_link}\n')

    return json_ok(msg='If that email is registered, a reset link has been sent.')
@routes.route('/api/reset-password/<token>', methods=['POST'])
def reset_password(token):
    body        = request.get_json(silent=True) or {}
    new_password = body.get('password', '')

    if len(new_password) < 8:
        return json_error('Password must be at least 8 characters.')

    record = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not record:
        return json_error('Invalid or already used reset link.', 400)
    if datetime.utcnow() > record.expires_at:
        return json_error('Reset link has expired.', 400)

    admin = Admin.query.get(record.admin_id)
    admin.password_hash = generate_password_hash(new_password)
    record.used = True
    db.session.commit()

    return json_ok(msg='Password reset successfully.')
@routes.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return json_ok(msg='Logged out successfully.')
@routes.route('/api/me', methods=['GET'])
@login_required
def me():
    return json_ok(data={'admin': current_user.to_dict()})

def _validate_opportunity(body):
    """Returns (error_string | None, cleaned_data_dict)."""
    name                 = (body.get('name') or '').strip()
    duration             = (body.get('duration') or '').strip()
    start_date           = (body.get('start_date') or '').strip()
    description          = (body.get('description') or '').strip()
    skills_raw           = (body.get('skills') or '').strip()
    category             = (body.get('category') or '').strip()
    future_opportunities = (body.get('future_opportunities') or '').strip()
    max_applicants_raw   = body.get('max_applicants')

    if not all([name, duration, start_date, description, skills_raw, category, future_opportunities]):
        return 'All required fields must be filled.', {}

    if category not in ALLOWED_CATEGORIES:
        return f'Category must be one of: {", ".join(ALLOWED_CATEGORIES)}.', {}

    max_applicants = None
    if max_applicants_raw not in (None, '', 0):
        try:
            max_applicants = int(max_applicants_raw)
            if max_applicants < 1:
                return 'Max applicants must be a positive number.', {}
        except (ValueError, TypeError):
            return 'Max applicants must be a number.', {}

    return None, {
        'name':                 name,
        'duration':             duration,
        'start_date':           start_date,
        'description':          description,
        'skills':               skills_raw,
        'category':             category,
        'future_opportunities': future_opportunities,
        'max_applicants':       max_applicants,
    }
@routes.route('/api/opportunities', methods=['GET'])
@login_required
def get_opportunities():
    ops = Opportunity.query.filter_by(admin_id=current_user.id)\
                           .order_by(Opportunity.created_at.desc()).all()
    return json_ok(data=[op.to_dict() for op in ops])
@routes.route('/api/opportunities', methods=['POST'])
@login_required
def add_opportunity():
    body = request.get_json(silent=True) or {}
    err, data = _validate_opportunity(body)
    if err:
        return json_error(err)

    op = Opportunity(admin_id=current_user.id, **data)
    db.session.add(op)
    db.session.commit()

    return json_ok(data=op.to_dict(), msg='Opportunity created.', code=201)
@routes.route('/api/opportunities/<int:op_id>', methods=['GET'])
@login_required
def get_opportunity(op_id):
    op = Opportunity.query.filter_by(id=op_id, admin_id=current_user.id).first()
    if not op:
        return json_error('Opportunity not found.', 404)
    return json_ok(data=op.to_dict())
@routes.route('/api/opportunities/<int:op_id>', methods=['PUT'])
@login_required
def edit_opportunity(op_id):
    op = Opportunity.query.filter_by(id=op_id, admin_id=current_user.id).first()
    if not op:
        return json_error('Opportunity not found.', 404)

    body = request.get_json(silent=True) or {}
    err, data = _validate_opportunity(body)
    if err:
        return json_error(err)

    for key, val in data.items():
        setattr(op, key, val)
    db.session.commit()

    return json_ok(data=op.to_dict(), msg='Opportunity updated.')
@routes.route('/api/opportunities/<int:op_id>', methods=['DELETE'])
@login_required
def delete_opportunity(op_id):
    op = Opportunity.query.filter_by(id=op_id, admin_id=current_user.id).first()
    if not op:
        return json_error('Opportunity not found.', 404)

    db.session.delete(op)
    db.session.commit()

    return json_ok(msg='Opportunity deleted.')