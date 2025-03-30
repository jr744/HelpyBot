import os
import json
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(16))

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Database models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class BannedUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    guild_id = db.Column(db.String(100), nullable=False) 
    reason = db.Column(db.String(200))
    banned_at = db.Column(db.DateTime, default=datetime.utcnow)
    banned_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'guild_id'),)

# Create all tables
with app.app_context():
    db.create_all()
    
    # Create a default super admin if none exists
    if not Admin.query.filter_by(is_super_admin=True).first():
        admin = Admin(username="admin", is_super_admin=True)
        admin.set_password("admin")
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created: admin / admin")

# Helper functions for JSON data
def load_bot_config():
    """Load bot configuration from JSON files"""
    guild_data = {}
    
    # Check for data directory
    if not os.path.exists('data'):
        os.makedirs('data', exist_ok=True)
    
    # Get all guild config files
    if os.path.exists('data/guilds'):
        for filename in os.listdir('data/guilds'):
            if filename.endswith('.json'):
                guild_id = filename.split('.')[0]
                guild_file = os.path.join('data/guilds', filename)
                
                try:
                    with open(guild_file, 'r', encoding='utf-8') as f:
                        guild_config = json.load(f)
                        
                    # Get panels
                    panels = {}
                    panels_dir = os.path.join('data/panels', guild_id)
                    if os.path.exists(panels_dir):
                        for panel_file in os.listdir(panels_dir):
                            if panel_file.endswith('.json'):
                                panel_id = panel_file.split('.')[0]
                                try:
                                    with open(os.path.join(panels_dir, panel_file), 'r', encoding='utf-8') as f:
                                        panels[panel_id] = json.load(f)
                                except:
                                    continue
                    
                    # Get tickets
                    tickets = {}
                    tickets_dir = os.path.join('data/tickets', guild_id)
                    if os.path.exists(tickets_dir):
                        for ticket_file in os.listdir(tickets_dir):
                            if ticket_file.endswith('.json'):
                                channel_id = ticket_file.split('.')[0]
                                try:
                                    with open(os.path.join(tickets_dir, ticket_file), 'r', encoding='utf-8') as f:
                                        tickets[channel_id] = json.load(f)
                                except:
                                    continue
                    
                    # Add to dict
                    guild_data[guild_id] = {
                        **guild_config,
                        'panels': panels,
                        'tickets': tickets
                    }
                except:
                    continue
    
    return guild_data

def save_bot_config(config_data):
    """Save bot configuration to JSON files"""
    # Ensure directories exist
    os.makedirs('data/guilds', exist_ok=True)
    os.makedirs('data/panels', exist_ok=True)
    os.makedirs('data/tickets', exist_ok=True)
    
    for guild_id, guild_config in config_data.items():
        # Create a copy of the guild config without panels and tickets
        guild_data = guild_config.copy()
        panels = guild_data.pop('panels', {})
        tickets = guild_data.pop('tickets', {})
        
        # Save guild config
        guild_file = os.path.join('data/guilds', f"{guild_id}.json")
        with open(guild_file, 'w', encoding='utf-8') as f:
            json.dump(guild_data, f, indent=2)
        
        # Save panels
        panels_dir = os.path.join('data/panels', guild_id)
        os.makedirs(panels_dir, exist_ok=True)
        for panel_id, panel_data in panels.items():
            panel_file = os.path.join(panels_dir, f"{panel_id}.json")
            with open(panel_file, 'w', encoding='utf-8') as f:
                json.dump(panel_data, f, indent=2)
        
        # Save tickets
        tickets_dir = os.path.join('data/tickets', guild_id)
        os.makedirs(tickets_dir, exist_ok=True)
        for channel_id, ticket_data in tickets.items():
            ticket_file = os.path.join(tickets_dir, f"{channel_id}.json")
            with open(ticket_file, 'w', encoding='utf-8') as f:
                json.dump(ticket_data, f, indent=2)

# Authentication decorator
def check_login():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes
@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['username'] = admin.username
            session['is_super_admin'] = admin.is_super_admin
            return redirect(url_for('dashboard'))
        else:
            flash('Nome de usuário ou senha incorretos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@check_login()
def dashboard():
    guild_data = load_bot_config()
    
    # Calculate statistics
    stats = {
        'guild_count': len(guild_data),
        'panel_count': sum(len(guild.get('panels', {})) for guild in guild_data.values()),
        'ticket_count': sum(len(guild.get('tickets', {})) for guild in guild_data.values()),
        'active_tickets': sum(1 for guild in guild_data.values() 
                             for ticket in guild.get('tickets', {}).values() 
                             if not ticket.get('closed', False))
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/guilds')
@check_login()
def guilds():
    guild_data = load_bot_config()
    return render_template('guilds.html', guilds=guild_data)

@app.route('/guilds/<guild_id>/config')
@check_login()
def guild_config(guild_id):
    guild_data = load_bot_config().get(guild_id, {})
    if not guild_data:
        flash('Servidor não encontrado', 'danger')
        return redirect(url_for('guilds'))
    
    return render_template('guild_config.html', guild_id=guild_id, guild_data=guild_data)

@app.route('/guilds/<guild_id>/config/update', methods=['POST'])
@check_login()
def update_guild_config(guild_id):
    guild_data = load_bot_config()
    
    if guild_id not in guild_data:
        flash('Servidor não encontrado', 'danger')
        return redirect(url_for('guilds'))
    
    # Update basic configuration
    guild_data[guild_id]['ticket_format'] = request.form.get('ticket_format', 'ticket-{number}')
    guild_data[guild_id]['max_tickets_per_user'] = int(request.form.get('max_tickets_per_user', 1))
    guild_data[guild_id]['inactivity_time'] = int(request.form.get('inactivity_time', 0))
    
    # Update boolean options
    guild_data[guild_id]['show_add_user_button'] = 'show_add_user_button' in request.form
    guild_data[guild_id]['show_remove_user_button'] = 'show_remove_user_button' in request.form
    guild_data[guild_id]['can_members_close'] = 'can_members_close' in request.form
    guild_data[guild_id]['auto_archive_tickets'] = 'auto_archive_tickets' in request.form
    guild_data[guild_id]['require_close_reason'] = 'require_close_reason' in request.form
    guild_data[guild_id]['notify_on_open'] = 'notify_on_open' in request.form
    
    # Save configuration
    save_bot_config(guild_data)
    
    flash('Configuração atualizada com sucesso', 'success')
    return redirect(url_for('guild_config', guild_id=guild_id))

@app.route('/guilds/<guild_id>/panels')
@check_login()
def guild_panels(guild_id):
    guild_data = load_bot_config().get(guild_id, {})
    if not guild_data:
        flash('Servidor não encontrado', 'danger')
        return redirect(url_for('guilds'))
    
    panels = guild_data.get('panels', {})
    return render_template('guild_panels.html', guild_id=guild_id, panels=panels)

@app.route('/guilds/<guild_id>/panels/<panel_id>/edit')
@check_login()
def edit_panel(guild_id, panel_id):
    guild_data = load_bot_config().get(guild_id, {})
    if not guild_data:
        flash('Servidor não encontrado', 'danger')
        return redirect(url_for('guilds'))
    
    panel = guild_data.get('panels', {}).get(panel_id)
    if not panel:
        flash('Painel não encontrado', 'danger')
        return redirect(url_for('guild_panels', guild_id=guild_id))
    
    return render_template('edit_panel.html', guild_id=guild_id, panel_id=panel_id, panel=panel)

@app.route('/guilds/<guild_id>/panels/<panel_id>/update', methods=['POST'])
@check_login()
def update_panel(guild_id, panel_id):
    guild_data = load_bot_config()
    
    if guild_id not in guild_data:
        flash('Servidor não encontrado', 'danger')
        return redirect(url_for('guilds'))
    
    panels = guild_data[guild_id].get('panels', {})
    if panel_id not in panels:
        flash('Painel não encontrado', 'danger')
        return redirect(url_for('guild_panels', guild_id=guild_id))
    
    # Update panel configuration
    panel = panels[panel_id]
    panel['title'] = request.form.get('title', panel.get('title', 'Ticket de Suporte'))
    panel['description'] = request.form.get('description', panel.get('description', 'Clique no botão abaixo para abrir um ticket.'))
    panel['color'] = request.form.get('color', panel.get('color', 'BLURPLE'))
    panel['button_style'] = request.form.get('button_style', panel.get('button_style', 'PRIMARY'))
    panel['button_text'] = request.form.get('button_text', panel.get('button_text', 'Abrir Ticket'))
    panel['button_emoji'] = request.form.get('button_emoji', panel.get('button_emoji', '🎫'))
    
    # Save configuration
    save_bot_config(guild_data)
    
    flash('Painel atualizado com sucesso', 'success')
    return redirect(url_for('edit_panel', guild_id=guild_id, panel_id=panel_id))

@app.route('/banned-users')
@check_login()
def banned_users():
    banned = BannedUser.query.order_by(BannedUser.banned_at.desc()).all()
    return render_template('banned_users.html', banned_users=banned)

@app.route('/ban-user', methods=['POST'])
@check_login()
def ban_user():
    user_id = request.form.get('user_id')
    guild_id = request.form.get('guild_id')
    reason = request.form.get('reason')
    
    # Check if user is already banned
    existing = BannedUser.query.filter_by(user_id=user_id, guild_id=guild_id).first()
    if existing:
        flash('Usuário já está banido neste servidor', 'warning')
        return redirect(url_for('banned_users'))
    
    # Create ban
    ban = BannedUser(
        user_id=user_id,
        guild_id=guild_id,
        reason=reason,
        banned_by=session.get('admin_id')
    )
    
    db.session.add(ban)
    db.session.commit()
    
    flash('Usuário banido com sucesso', 'success')
    return redirect(url_for('banned_users'))

@app.route('/unban-user/<int:ban_id>')
@check_login()
def unban_user(ban_id):
    ban = BannedUser.query.get_or_404(ban_id)
    
    db.session.delete(ban)
    db.session.commit()
    
    flash('Banimento removido com sucesso', 'success')
    return redirect(url_for('banned_users'))

@app.route('/admins')
@check_login()
def admins():
    # Only super admins can access this page
    if not session.get('is_super_admin'):
        flash('Acesso negado', 'danger')
        return redirect(url_for('dashboard'))
    
    admin_list = Admin.query.all()
    return render_template('admins.html', admins=admin_list)

@app.route('/admins/add', methods=['POST'])
@check_login()
def add_admin():
    # Only super admins can add other admins
    if not session.get('is_super_admin'):
        flash('Acesso negado', 'danger')
        return redirect(url_for('dashboard'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    is_super_admin = request.form.get('is_super_admin') == 'on'
    
    # Check if username already exists
    existing = Admin.query.filter_by(username=username).first()
    if existing:
        flash('Nome de usuário já existe', 'danger')
        return redirect(url_for('admins'))
    
    # Create admin
    admin = Admin(username=username, is_super_admin=is_super_admin)
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    flash('Administrador adicionado com sucesso', 'success')
    return redirect(url_for('admins'))

@app.route('/admins/delete/<int:admin_id>')
@check_login()
def delete_admin(admin_id):
    # Only super admins can delete other admins
    if not session.get('is_super_admin'):
        flash('Acesso negado', 'danger')
        return redirect(url_for('dashboard'))
    
    # Cannot delete yourself
    if admin_id == session.get('admin_id'):
        flash('Você não pode excluir sua própria conta', 'danger')
        return redirect(url_for('admins'))
    
    admin = Admin.query.get_or_404(admin_id)
    
    db.session.delete(admin)
    db.session.commit()
    
    flash('Administrador excluído com sucesso', 'success')
    return redirect(url_for('admins'))

# API endpoint to check if a user is banned
@app.route('/api/check-banned', methods=['POST'])
def check_banned():
    data = request.json
    user_id = data.get('user_id')
    guild_id = data.get('guild_id')
    
    if not user_id or not guild_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    ban = BannedUser.query.filter_by(user_id=user_id, guild_id=guild_id).first()
    
    if ban:
        return jsonify({
            'banned': True,
            'reason': ban.reason,
            'banned_at': ban.banned_at.isoformat()
        })
    
    return jsonify({'banned': False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)