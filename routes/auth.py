import os
import jwt
import time
from flask import Blueprint, jsonify, request
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# Chave secreta para JWT (em produção, usar variável de ambiente)
JWT_SECRET = os.environ.get('JWT_SECRET', 'prod_zpl_secret_2024_' + str(int(time.time())))

def require_auth(f):
    """Decorator para rotas que requerem autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Verificar token no header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer TOKEN
            except IndexError:
                return jsonify({'error': 'Token inválido'}), 401
        
        if not token:
            return jsonify({'error': 'Token de acesso necessário'}), 401
        
        try:
            # Decodificar o token
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated_function

@auth_bp.route('/verify-auth', methods=['POST'])
def verify_auth():
    """Verificar se o token de autenticação é válido"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'valid': False, 'error': 'Token não fornecido'}), 400
        
        # Decodificar o token
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        return jsonify({
            'valid': True,
            'user_id': decoded['user_id'],
            'email': decoded.get('email', ''),
            'expires_at': decoded['exp']
        })
        
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'error': 'Token expirado'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'valid': False, 'error': 'Token inválido'}), 401
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500

@auth_bp.route('/manus-callback', methods=['POST'])
def manus_callback():
    """Callback para receber dados do usuário após login na Manus"""
    try:
        data = request.get_json()
        
        # Dados que esperamos receber da Manus
        user_id = data.get('user_id')
        email = data.get('email')
        name = data.get('name', '')
        
        if not user_id or not email:
            return jsonify({'error': 'Dados de usuário incompletos'}), 400
        
        # Criar token JWT para o usuário
        payload = {
            'user_id': user_id,
            'email': email,
            'name': name,
            'iat': int(time.time()),
            'exp': int(time.time()) + (30 * 24 * 60 * 60)  # 30 dias
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'name': name
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro no callback: {str(e)}'}), 500

@auth_bp.route('/create-demo-token', methods=['POST'])
def create_demo_token():
    """Criar token de demonstração (temporário para testes)"""
    try:
        data = request.get_json()
        email = data.get('email', 'demo@example.com')
        
        # Criar token JWT de demonstração
        payload = {
            'user_id': f'demo_{int(time.time())}',
            'email': email,
            'name': 'Usuário Demo',
            'iat': int(time.time()),
            'exp': int(time.time()) + (30 * 24 * 60 * 60)  # 30 dias
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': payload['user_id'],
                'email': email,
                'name': 'Usuário Demo'
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao criar token demo: {str(e)}'}), 500

@auth_bp.route('/user-info', methods=['GET'])
@require_auth
def user_info(current_user):
    """Obter informações do usuário autenticado"""
    try:
        # Como é gratuito, sempre retornar créditos ilimitados
        return jsonify({
            'user_id': current_user,
            'credits': 999999,  # Ilimitado
            'plan': 'free',
            'status': 'active'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao obter informações: {str(e)}'}), 500

