import os
import json
import logging

# Configuração de logging
logger = logging.getLogger('database')

# Caminhos para os arquivos JSON
DATA_DIR = 'data'
CONFIG_FILE = os.path.join(DATA_DIR, 'configs.json')
EDIT_SESSIONS_FILE = os.path.join(DATA_DIR, 'edit_sessions.json')

# Cria o diretório de dados se não existir
os.makedirs(DATA_DIR, exist_ok=True)

# Funções de utilidade para carregar e salvar dados JSON
def _load_json(file_path):
    """Carrega dados de um arquivo JSON"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Erro ao carregar arquivo JSON {file_path}: {e}")
        return {}

def _save_json(file_path, data):
    """Salva dados em um arquivo JSON"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo JSON {file_path}: {e}")
        return False

# Classes de modelo (agora apenas para definir a estrutura)
class Guild:
    """Modelo para as configurações de cada servidor (guild)"""
    
    @staticmethod
    def get_default_config():
        """Retorna as configurações padrão para um servidor"""
        return {
            'next_ticket_number': 1,
            'show_add_user_button': True,
            'show_remove_user_button': True,
            'max_tickets_per_user': 1,
            'can_members_close': True,
            'inactivity_time': 0,  # Em horas (0 = desativado)
            'auto_archive_tickets': False,
            'require_close_reason': True,
            'notify_on_open': False,
            'ticket_format': "ticket-{number}",
            'panels': {},
            'tickets': {}
        }
    
    @staticmethod
    def get(guild_id):
        """Obtém as configurações de um servidor"""
        configs = _load_json(CONFIG_FILE)
        
        if guild_id not in configs:
            configs[guild_id] = Guild.get_default_config()
            _save_json(CONFIG_FILE, configs)
            
        return configs[guild_id]
    
    @staticmethod
    def update(guild_id, data):
        """Atualiza as configurações de um servidor"""
        configs = _load_json(CONFIG_FILE)
        
        if guild_id not in configs:
            configs[guild_id] = Guild.get_default_config()
            
        # Atualiza apenas os campos fornecidos
        for key, value in data.items():
            if key in configs[guild_id]:
                configs[guild_id][key] = value
                
        return _save_json(CONFIG_FILE, configs)

class Panel:
    """Modelo para os painéis de ticket de cada servidor"""
    
    @staticmethod
    def get_default():
        """Retorna as configurações padrão para um painel"""
        return {
            'panel_name': "Painel sem nome",
            'title': "Suporte",
            'description': "Clique no botão abaixo para abrir um ticket.",
            'color': "#3498db",
            'support_role_id': None,
            'category_id': None,
            'use_button': True,
            'button_style': "blurple",
            'button_emoji': None,
            'button_text': "Abrir Ticket",
            'dropdown_placeholder': "Selecione um motivo",
            'dropdown_options': [],
            'welcome_message': None,
            'instruction_message': None
        }
    
    @staticmethod
    def get(guild_id, panel_id):
        """Obtém um painel específico de um servidor"""
        guild_config = Guild.get(guild_id)
        
        if 'panels' not in guild_config:
            guild_config['panels'] = {}
            Guild.update(guild_id, {'panels': {}})
        
        if panel_id not in guild_config['panels']:
            return None
            
        return guild_config['panels'][panel_id]
    
    @staticmethod
    def get_all(guild_id):
        """Obtém todos os painéis de um servidor"""
        guild_config = Guild.get(guild_id)
        
        if 'panels' not in guild_config:
            guild_config['panels'] = {}
            Guild.update(guild_id, {'panels': {}})
            
        return guild_config['panels']
    
    @staticmethod
    def create(guild_id, panel_id, panel_data=None):
        """Cria um novo painel para um servidor"""
        if panel_data is None:
            panel_data = Panel.get_default()
            
        guild_config = Guild.get(guild_id)
        
        if 'panels' not in guild_config:
            guild_config['panels'] = {}
        
        guild_config['panels'][panel_id] = panel_data
        return Guild.update(guild_id, {'panels': guild_config['panels']})
    
    @staticmethod
    def update(guild_id, panel_id, panel_data):
        """Atualiza um painel existente"""
        guild_config = Guild.get(guild_id)
        
        if 'panels' not in guild_config:
            guild_config['panels'] = {}
        
        if panel_id not in guild_config['panels']:
            guild_config['panels'][panel_id] = Panel.get_default()
        
        # Atualiza apenas os campos fornecidos
        for key, value in panel_data.items():
            guild_config['panels'][panel_id][key] = value
            
        return Guild.update(guild_id, {'panels': guild_config['panels']})
    
    @staticmethod
    def delete(guild_id, panel_id):
        """Exclui um painel"""
        guild_config = Guild.get(guild_id)
        
        if 'panels' not in guild_config or panel_id not in guild_config['panels']:
            return False
        
        del guild_config['panels'][panel_id]
        return Guild.update(guild_id, {'panels': guild_config['panels']})

class Ticket:
    """Modelo para os tickets abertos em cada servidor"""
    
    @staticmethod
    def get_default():
        """Retorna as configurações padrão para um ticket"""
        return {
            'creator_id': None,
            'panel_id': None,
            'ticket_number': 0,
            'ticket_type': None,
            'status': "open",  # open, closed, archived
            'claimed_by': None,
            'priority': "none"  # none, low, medium, high
        }
    
    @staticmethod
    def get(guild_id, channel_id):
        """Obtém um ticket específico de um servidor"""
        guild_config = Guild.get(guild_id)
        
        if 'tickets' not in guild_config:
            guild_config['tickets'] = {}
            Guild.update(guild_id, {'tickets': {}})
        
        if channel_id not in guild_config['tickets']:
            return None
            
        return guild_config['tickets'][channel_id]
    
    @staticmethod
    def get_all(guild_id):
        """Obtém todos os tickets de um servidor"""
        guild_config = Guild.get(guild_id)
        
        if 'tickets' not in guild_config:
            guild_config['tickets'] = {}
            Guild.update(guild_id, {'tickets': {}})
            
        return guild_config['tickets']
    
    @staticmethod
    def create(guild_id, channel_id, ticket_data=None):
        """Cria um novo ticket para um servidor"""
        if ticket_data is None:
            ticket_data = Ticket.get_default()
            
        guild_config = Guild.get(guild_id)
        
        if 'tickets' not in guild_config:
            guild_config['tickets'] = {}
        
        # Incrementa o número do ticket se necessário
        if 'ticket_number' not in ticket_data or ticket_data['ticket_number'] == 0:
            ticket_data['ticket_number'] = guild_config['next_ticket_number']
            guild_config['next_ticket_number'] += 1
            Guild.update(guild_id, {'next_ticket_number': guild_config['next_ticket_number']})
        
        guild_config['tickets'][channel_id] = ticket_data
        return Guild.update(guild_id, {'tickets': guild_config['tickets']})
    
    @staticmethod
    def update(guild_id, channel_id, ticket_data):
        """Atualiza um ticket existente"""
        guild_config = Guild.get(guild_id)
        
        if 'tickets' not in guild_config:
            guild_config['tickets'] = {}
        
        if channel_id not in guild_config['tickets']:
            return False
        
        # Atualiza apenas os campos fornecidos
        for key, value in ticket_data.items():
            guild_config['tickets'][channel_id][key] = value
            
        return Guild.update(guild_id, {'tickets': guild_config['tickets']})
    
    @staticmethod
    def delete(guild_id, channel_id):
        """Exclui um ticket"""
        guild_config = Guild.get(guild_id)
        
        if 'tickets' not in guild_config or channel_id not in guild_config['tickets']:
            return False
        
        del guild_config['tickets'][channel_id]
        return Guild.update(guild_id, {'tickets': guild_config['tickets']})
    
    @staticmethod
    def count_user_tickets(guild_id, user_id):
        """Conta o número de tickets abertos de um usuário"""
        guild_config = Guild.get(guild_id)
        
        if 'tickets' not in guild_config:
            return 0
        
        count = 0
        for ticket_id, ticket in guild_config['tickets'].items():
            if ticket['creator_id'] == user_id and ticket['status'] == 'open':
                count += 1
                
        return count

class EditSession:
    """Modelo para as sessões de edição de painéis"""
    
    @staticmethod
    def get(user_id, guild_id):
        """Obtém uma sessão de edição"""
        session_id = f"{user_id}:{guild_id}"
        sessions = _load_json(EDIT_SESSIONS_FILE)
        
        if session_id not in sessions:
            return None
            
        return sessions[session_id]
    
    @staticmethod
    def create(user_id, guild_id, panel_data):
        """Cria uma nova sessão de edição"""
        session_id = f"{user_id}:{guild_id}"
        sessions = _load_json(EDIT_SESSIONS_FILE)
        
        sessions[session_id] = {
            'panel_data': panel_data
        }
        
        return _save_json(EDIT_SESSIONS_FILE, sessions)
    
    @staticmethod
    def update(user_id, guild_id, panel_data):
        """Atualiza uma sessão de edição existente"""
        session_id = f"{user_id}:{guild_id}"
        sessions = _load_json(EDIT_SESSIONS_FILE)
        
        if session_id not in sessions:
            sessions[session_id] = {}
            
        sessions[session_id]['panel_data'] = panel_data
        
        return _save_json(EDIT_SESSIONS_FILE, sessions)
    
    @staticmethod
    def delete(user_id, guild_id):
        """Exclui uma sessão de edição"""
        session_id = f"{user_id}:{guild_id}"
        sessions = _load_json(EDIT_SESSIONS_FILE)
        
        if session_id not in sessions:
            return False
        
        del sessions[session_id]
        return _save_json(EDIT_SESSIONS_FILE, sessions)

# Inicializa os arquivos se não existirem
if not os.path.exists(CONFIG_FILE):
    _save_json(CONFIG_FILE, {})
    
if not os.path.exists(EDIT_SESSIONS_FILE):
    _save_json(EDIT_SESSIONS_FILE, {})