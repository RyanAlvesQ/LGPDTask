from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from cryptography.fernet import Fernet
import mysql.connector
import logging

app = Flask(__name__)

# Configuração da chave para criptografia e descriptografia
def load_key():
    return open("secret.key", "rb").read()

# Configuração do JWT
app.config['JWT_SECRET_KEY'] = 'super-secret'
jwt = JWTManager(app)

# Configuração do logger
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Função para criptografar dados
def encrypt_data(data: str) -> bytes:
    key = load_key()
    fernet = Fernet(key)
    return fernet.encrypt(data.encode())

# Função para descriptografar dados
def decrypt_data(encrypted_data: bytes) -> str:
    key = load_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data).decode()

def connect_to_database():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="lgpd_db"
    )

    create_table_query = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        idade INT NOT NULL,
        cpf TEXT NOT NULL,
        rg TEXT NOT NULL
    )
    """

    try:
        cursor = conn.cursor()
        cursor.execute(create_table_query)
        conn.commit()
        cursor.close()
    except mysql.connector.Error as err:
        print(f"Erro ao criar tabela de usuários: {err}")

    return conn

def create_user(nome, idade, cpf, rg):
    conn = None
    try:
        conn = connect_to_database()
        cursor = conn.cursor()

        encrypted_cpf = encrypt_data(cpf)
        encrypted_rg = encrypt_data(rg)

        sql = "INSERT INTO usuarios (nome, idade, cpf, rg) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nome, idade, encrypted_cpf, encrypted_rg))
        conn.commit()

        cursor.close()
        print("Usuário criado com sucesso!")
    except mysql.connector.Error as err:
        print(f"Erro ao criar usuário: {err}")
    finally:
        if conn:
            conn.close()

def read_users(role):
    users = []
    try:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios")
        rows = cursor.fetchall()

        for row in rows:
            nome = row[1]
            idade = row[2]
            encrypted_cpf = row[3]
            encrypted_rg = row[4]

            # Verifica a role do admin para decidir se descriptografa os dados
            if role == 'pleno':
                decrypted_cpf = decrypt_data(encrypted_cpf)
                decrypted_rg = decrypt_data(encrypted_rg)
            elif role == 'junior':
                decrypted_cpf = encrypted_cpf
                decrypted_rg = encrypted_rg
            else:
                decrypted_cpf = encrypted_cpf
                decrypted_rg = encrypted_rg

            user_data = {
                'nome': nome,
                'idade': idade,
                'cpf': decrypted_cpf,
                'rg': decrypted_rg
            }
            users.append(user_data)

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Erro ao buscar usuários: {err}")

    return users

def get_admin_by_username(username):
    conn = connect_to_database()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM admin WHERE username = %s"
    cursor.execute(query, (username,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    return admin

# Função para registrar eventos no log
def log_event(message):
    logging.info(message)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Credenciais não fornecidas ou formato inválido'}), 400
        
    username = data['username']
    password = data['password']

    admin = get_admin_by_username(username)

    if admin and admin['password'] == password:
        access_token = create_access_token(identity=username, additional_claims={'role': admin['role']})
        log_event(f"Login bem-sucedido para o admin: {username}")
        return jsonify({'access_token': access_token}), 200
    else:
        log_event(f"Tentativa de login inválida para o usuário: {username}")
        return jsonify({'message': 'Credenciais inválidas'}), 401

@app.route('/criar-usuario', methods=['POST'])
@jwt_required()
def criar_usuario_protegido():
    current_user = get_jwt_identity()
    admin = get_admin_by_username(current_user)

    if not admin or admin['role'] != 'pleno':
        log_event(f"Tentativa de acesso não autorizado pelo usuário: {current_user}")
        return jsonify({'message': 'Acesso não autorizado'}), 403

    data = request.get_json()
    nome = data.get('nome')
    idade = data.get('idade')
    cpf = data.get('cpf')
    rg = data.get('rg')

    create_user(nome, idade, cpf, rg)
    log_event(f"Novo usuário criado por admin: {current_user}")
    return jsonify({'message': 'Usuário criado com sucesso!'}), 200


@app.route('/ler-usuarios', methods=['GET'])
@jwt_required()
def ler_usuarios_protegido():
    current_user = get_jwt_identity()
    admin = get_admin_by_username(current_user)

    if not admin:
        log_event(f"Tentativa de acesso não autorizado pelo usuário: {current_user}")
        return jsonify({'message': 'Admin não encontrado'}), 404

    role = admin['role']

    if role not in ['pleno', 'junior']:
        log_event(f"Acesso não autorizado por admin: {current_user}")
        return jsonify({'message': 'Role inválida'}), 403

    users = read_users(role)
    return jsonify({'users': users, 'message': 'Listagem de usuários concluída'}), 200

if __name__ == "__main__":
    app.run(port=3001)
