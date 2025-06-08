import os
import logging
from configparser import ConfigParser
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler, TLS_FTPHandler
from pyftpdlib.servers import FTPServer

# Configuração de log
logger = logging.getLogger(__name__)


def create_config_interactively():
    """Prompt the user for initial server configuration and write config.ini."""
    print("Arquivo config.ini nao encontrado. Iniciando configuracao inicial.")

    config = ConfigParser()

    host = input("Host [127.0.0.1]: ") or "127.0.0.1"
    port = input("Porta [2121]: ") or "2121"
    master_user = input("Usuario mestre [master]: ") or "master"
    master_pass = input("Senha do mestre [pass]: ") or "pass"
    default_user = input("Usuario padrao [user]: ") or "user"
    default_pass = input("Senha do padrao [pass]: ") or "pass"
    allowed_path = input("Caminho permitido [/tmp]: ") or "/tmp"
    ip_whitelist = input("IPs liberados (separados por virgula) [127.0.0.1]: ") or "127.0.0.1"
    ip_blacklist = input("IPs bloqueados (separados por virgula) []: ") or ""
    use_tls = input("Habilitar TLS? (s/n) [n]: ").lower() in {"s", "y"}
    max_conn = input("Maximo de conexoes [256]: ") or "256"
    max_conn_ip = input("Maximo de conexoes por IP [5]: ") or "5"
    timeout = input("Timeout [120]: ") or "120"
    log_level = input("Nivel de log [INFO]: ") or "INFO"
    encryption_enabled = input("Habilitar criptografia? (s/n) [n]: ").lower() in {"s", "y"}
    enc_key = ""
    if encryption_enabled:
        enc_key = input("Chave de criptografia: ")

    config["FTP_SERVER"] = {
        "FTP_HOST": host,
        "FTP_PORT": port,
        "USE_TLS": str(use_tls),
        "CERTFILE": "",
        "KEYFILE": "",
        "MAX_CONNECTIONS": max_conn,
        "MAX_CONNECTIONS_PER_IP": max_conn_ip,
        "TIMEOUT": timeout,
        "LOG_LEVEL": log_level,
        "ENCRYPTION_ENABLED": str(encryption_enabled),
        "ENCRYPTION_KEY": enc_key,
    }

    config["USERS"] = {
        "FTP_USER_MASTER": master_user,
        "FTP_PASSWORD_MASTER": master_pass,
        "FTP_PERM_MASTER": "elradfmw",
        "FTP_USER_DEFAULT": default_user,
        "FTP_PASSWORD_DEFAULT": default_pass,
        "FTP_PERM_DEFAULT": "elr",
    }

    config["PATH"] = {"ALLOWED_PATH": allowed_path}
    config["IP"] = {
        "IP_WHITELIST": ip_whitelist,
        "IP_BLACKLIST": ip_blacklist,
    }

    with open("config.ini", "w") as f:
        config.write(f)

    print("Arquivo config.ini criado com sucesso.")


def load_config():
    config = ConfigParser()
    config.read('config.ini')

    # Configurações do servidor FTP
    FTP_HOST = config.get('FTP_SERVER', 'FTP_HOST')
    FTP_PORT = config.getint('FTP_SERVER', 'FTP_PORT')

    # Credenciais e permissões dos usuários
    FTP_USER_MASTER = config.get('USERS', 'FTP_USER_MASTER')
    FTP_PASSWORD_MASTER = config.get('USERS', 'FTP_PASSWORD_MASTER')
    FTP_PERM_MASTER = config.get('USERS', 'FTP_PERM_MASTER')

    FTP_USER_DEFAULT = config.get('USERS', 'FTP_USER_DEFAULT')
    FTP_PASSWORD_DEFAULT = config.get('USERS', 'FTP_PASSWORD_DEFAULT')
    FTP_PERM_DEFAULT = config.get('USERS', 'FTP_PERM_DEFAULT')

    # Caminho permitido
    ALLOWED_PATH = config.get('PATH', 'ALLOWED_PATH')

    # IPs permitidos (Whitelist)
    IP_WHITELIST = [ip.strip() for ip in config.get('IP', 'IP_WHITELIST').split(',')]

    # IPs bloqueados (Blacklist)
    IP_BLACKLIST = [ip.strip() for ip in config.get('IP', 'IP_BLACKLIST').split(',')]

    # Opções adicionais
    USE_TLS = config.getboolean('FTP_SERVER', 'USE_TLS', fallback=False)
    CERTFILE = config.get('FTP_SERVER', 'CERTFILE', fallback='')
    KEYFILE = config.get('FTP_SERVER', 'KEYFILE', fallback='')
    MAX_CONNECTIONS = config.getint('FTP_SERVER', 'MAX_CONNECTIONS', fallback=256)
    MAX_CONNECTIONS_PER_IP = config.getint('FTP_SERVER', 'MAX_CONNECTIONS_PER_IP', fallback=5)
    TIMEOUT = config.getint('FTP_SERVER', 'TIMEOUT', fallback=120)
    LOG_LEVEL = config.get('FTP_SERVER', 'LOG_LEVEL', fallback='INFO').upper()
    ENCRYPTION_ENABLED = config.getboolean('FTP_SERVER', 'ENCRYPTION_ENABLED', fallback=False)
    ENCRYPTION_KEY = config.get('FTP_SERVER', 'ENCRYPTION_KEY', fallback='')

    return (
        FTP_HOST,
        FTP_PORT,
        FTP_USER_MASTER,
        FTP_PASSWORD_MASTER,
        FTP_PERM_MASTER,
        FTP_USER_DEFAULT,
        FTP_PASSWORD_DEFAULT,
        FTP_PERM_DEFAULT,
        ALLOWED_PATH,
        IP_WHITELIST,
        IP_BLACKLIST,
        USE_TLS,
        CERTFILE,
        KEYFILE,
        MAX_CONNECTIONS,
        MAX_CONNECTIONS_PER_IP,
        TIMEOUT,
        LOG_LEVEL,
        ENCRYPTION_ENABLED,
        ENCRYPTION_KEY,
    )


def start_ftp_server():
    (
        FTP_HOST,
        FTP_PORT,
        FTP_USER_MASTER,
        FTP_PASSWORD_MASTER,
        FTP_PERM_MASTER,
        FTP_USER_DEFAULT,
        FTP_PASSWORD_DEFAULT,
        FTP_PERM_DEFAULT,
        ALLOWED_PATH,
        IP_WHITELIST,
        IP_BLACKLIST,
        USE_TLS,
        CERTFILE,
        KEYFILE,
        MAX_CONNECTIONS,
        MAX_CONNECTIONS_PER_IP,
        TIMEOUT,
        LOG_LEVEL,
        ENCRYPTION_ENABLED,
        ENCRYPTION_KEY,
    ) = load_config()

    # Cria um objeto authorizer com credenciais dummy
    authorizer = DummyAuthorizer()

    # Adiciona o usuário mestre com permissão full
    authorizer.add_user(FTP_USER_MASTER, FTP_PASSWORD_MASTER, '.', perm=FTP_PERM_MASTER)

    # Adiciona o usuário padrão com permissão de upload somente na unidade permitida
    authorizer.add_user(FTP_USER_DEFAULT, FTP_PASSWORD_DEFAULT, ALLOWED_PATH, perm=FTP_PERM_DEFAULT)

    # Função para verificar se o caminho está dentro da unidade permitida
    def check_path(path):
        return os.path.abspath(path).startswith(os.path.abspath(ALLOWED_PATH))

    # Função para verificar se o IP está na whitelist
    def check_ip_whitelist(remote_ip):
        return remote_ip in IP_WHITELIST

    # Função para verificar se o IP está na blacklist
    def check_ip_blacklist(remote_ip):
        return remote_ip in IP_BLACKLIST

    # Define o handler baseado na configuração de TLS
    base_handler = TLS_FTPHandler if USE_TLS else FTPHandler

    # Subclasse FTPHandler para adicionar verificação personalizada
    class MyHandler(base_handler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.timeout = TIMEOUT

        def ftp_STOR(self, file, mode='w'):
            if not check_path(file):
                self.respond("553 Permission denied")
                return
            if not check_ip_whitelist(self.remote_ip):
                self.respond("553 Permission denied: IP not in whitelist")
                return
            if check_ip_blacklist(self.remote_ip):
                self.respond("553 Permission denied: IP in blacklist")
                return

            result = super().ftp_STOR(file, mode)
            if result.startswith("226"):
                logger.info(f"Arquivo enviado com sucesso: {file} por {self.username}")
            return result

        def ftp_RETR(self, file):
            self.respond("553 Permission denied: Download não permitido para o usuário padrão")

        def ftp_MKD(self, path):
            if not check_path(path):
                self.respond("553 Permission denied")
                return
            if not check_ip_whitelist(self.remote_ip):
                self.respond("553 Permission denied: IP not in whitelist")
                return
            if check_ip_blacklist(self.remote_ip):
                self.respond("553 Permission denied: IP in blacklist")
                return
            result = super().ftp_MKD(path)
            if result.startswith("257"):
                logger.info(f"Diretório criado com sucesso: {path} por {self.username}")
            return result

        def ftp_RMD(self, path):
            if not check_path(path):
                self.respond("553 Permission denied")
                return
            if not check_ip_whitelist(self.remote_ip):
                self.respond("553 Permission denied: IP not in whitelist")
                return
            if check_ip_blacklist(self.remote_ip):
                self.respond("553 Permission denied: IP in blacklist")
                return
            result = super().ftp_RMD(path)
            if result.startswith("250"):
                logger.info(f"Diretório removido com sucesso: {path} por {self.username}")
            return result

        def ftp_DELE(self, path):
            if not check_path(path):
                self.respond("553 Permission denied")
                return
            if not check_ip_whitelist(self.remote_ip):
                self.respond("553 Permission denied: IP not in whitelist")
                return
            if check_ip_blacklist(self.remote_ip):
                self.respond("553 Permission denied: IP in blacklist")
                return
            result = super().ftp_DELE(path)
            if result.startswith("250"):
                logger.info(f"Arquivo removido com sucesso: {path} por {self.username}")
            return result

        def ftp_RNFR(self, path):
            if not check_path(path):
                self.respond("553 Permission denied")
                return
            if not check_ip_whitelist(self.remote_ip):
                self.respond("553 Permission denied: IP not in whitelist")
                return
            if check_ip_blacklist(self.remote_ip):
                self.respond("553 Permission denied: IP in blacklist")
                return
            result = super().ftp_RNFR(path)
            if result.startswith("350"):
                logger.info(f"Renomeação de arquivo iniciada: {path} por {self.username}")
            return result

        def ftp_RNTO(self, path):
            if not check_path(path):
                self.respond("553 Permission denied")
                return
            if not check_ip_whitelist(self.remote_ip):
                self.respond("553 Permission denied: IP not in whitelist")
                return
            if check_ip_blacklist(self.remote_ip):
                self.respond("553 Permission denied: IP in blacklist")
                return
            result = super().ftp_RNTO(path)
            if result.startswith("250"):
                logger.info(f"Arquivo renomeado com sucesso para: {path} por {self.username}")
            return result

        def ftp_APPE(self, file):
            if not check_path(file):
                self.respond("553 Permission denied")
                return
            if not check_ip_whitelist(self.remote_ip):
                self.respond("553 Permission denied: IP not in whitelist")
                return
            if check_ip_blacklist(self.remote_ip):
                self.respond("553 Permission denied: IP in blacklist")
                return

            result = super().ftp_APPE(file)
            if result.startswith("226"):
                logger.info(f"Conteúdo adicionado com sucesso ao arquivo: {file} por {self.username}")
            return result

        def on_login(self, username):
            logger.info(f'Usuário {username} logado com sucesso')

        def on_logout(self, username):
            logger.info(f'Usuário {username} deslogado com sucesso')

        def on_login_failed(self, username):
            logger.info(f'Falha no login para o usuário {username}')

        def on_file_sent(self, file):
            logger.info(f'Arquivo enviado: {file}')

        def on_connect(self):
            if check_ip_blacklist(self.remote_ip):
                self.respond("530 Permission denied: IP in blacklist")
                self.close()
                return
            logger.info(f'Conexão estabelecida do IP: {self.remote_ip}')

        def on_disconnect(self):
            logger.info(f'Desconexão do IP: {self.remote_ip}')

        def on_file_received(self, file):
            logger.info(f'Arquivo recebido: {file}')

        def on_incomplete_file_received(self, file):
            logger.info(f'Arquivo recebido incompleto: {file}')

        def on_delete_file_failed(self, file):
            logger.info(f'Falha ao remover arquivo: {file}')

        def on_delete_directory_failed(self, path):
            logger.info(f'Falha ao remover diretório: {path}')

        def on_rename_failed(self, fromname, toname):
            logger.info(f'Falha ao renomear arquivo de {fromname} para {toname}')

        def on_mkdir_failed(self, path):
            logger.info(f'Falha ao criar diretório: {path}')

        def on_file_sent_failed(self, file):
            logger.info(f'Falha ao enviar arquivo: {file}')

        def on_file_received_failed(self, file):
            logger.info(f'Falha ao receber arquivo: {file}')

        def server_quit(self):
            logger.info('Servidor encerrado')

        def server_starting(self, evt):
            logger.info('Iniciando servidor FTP...')

    # Cria um handler FTP com a verificação personalizada
    handler = MyHandler
    handler.authorizer = authorizer
    if USE_TLS and CERTFILE:
        handler.certfile = CERTFILE
        if KEYFILE:
            handler.keyfile = KEYFILE
        handler.tls_control_required = True
        handler.tls_data_required = True

    # Configura o endereço e porta do servidor
    server = FTPServer((FTP_HOST, FTP_PORT), handler)
    server.max_cons = MAX_CONNECTIONS
    server.max_cons_per_ip = MAX_CONNECTIONS_PER_IP

    # Inicia o servidor FTP
    logger.info(f'Servidor FTP iniciado em {FTP_HOST}:{FTP_PORT}')
    server.serve_forever()
    logger.info('Parando servidor FTP...')


if __name__ == '__main__':
    if not os.path.exists('config.ini'):
        create_config_interactively()

    (
        FTP_HOST,
        FTP_PORT,
        FTP_USER_MASTER,
        FTP_PASSWORD_MASTER,
        FTP_PERM_MASTER,
        FTP_USER_DEFAULT,
        FTP_PASSWORD_DEFAULT,
        FTP_PERM_DEFAULT,
        ALLOWED_PATH,
        IP_WHITELIST,
        IP_BLACKLIST,
        USE_TLS,
        CERTFILE,
        KEYFILE,
        MAX_CONNECTIONS,
        MAX_CONNECTIONS_PER_IP,
        TIMEOUT,
        LOG_LEVEL,
        ENCRYPTION_ENABLED,
        ENCRYPTION_KEY,
    ) = load_config()

    log_level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        filename='ftp_server.log',
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(console)
    logger.info('Carregando configurações do servidor FTP...')
    logger.info('Lendo configurações do arquivo config.ini...')

    print(f'Servidor FTP iniciado em {FTP_HOST}:{FTP_PORT}...')
    logger.info(f'Servidor FTP sendo iniciado em {FTP_HOST}:{FTP_PORT}...')
    start_ftp_server()

# Para executar o servidor, basta rodar o script FTP_server.py


