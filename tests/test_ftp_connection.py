import os
import sys
# Ensure module import from repository root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import types

# Provide dummy pyftpdlib modules so FTP_server can be imported without the
# real dependency installed.
sys.modules.setdefault('pyftpdlib.authorizers', types.SimpleNamespace(DummyAuthorizer=object))
sys.modules.setdefault('pyftpdlib.handlers', types.SimpleNamespace(
    FTPHandler=object,
    TLS_FTPHandler=object,
))
sys.modules.setdefault('pyftpdlib.servers', types.SimpleNamespace(FTPServer=object))

import FTP_Connection
import FTP_server

class FakeFTP:
    def __init__(self):
        self.stored = {}
        self.files = {}

    def storbinary(self, cmd, file):
        filename = cmd.split()[1]
        self.stored[filename] = file.read()

    def retrbinary(self, cmd, callback):
        filename = cmd.split()[1]
        data = self.files.get(filename)
        if data is None:
            raise Exception('missing file')
        callback(data)

def test_load_config(tmp_path):
    cfg = tmp_path / 'config.ini'
    cfg.write_text('[FTP_SERVER]\n'
                    'FTP_HOST=127.0.0.1\nFTP_PORT=2121\n'
                    'USE_TLS=False\n'
                    'MAX_CONNECTIONS=100\n'
                    'MAX_CONNECTIONS_PER_IP=2\n'
                    'TIMEOUT=60\n'
                    'LOG_LEVEL=DEBUG\n'
                    '[USERS]\nFTP_USER_MASTER=master\n'
                    'FTP_PASSWORD_MASTER=pass\n'
                    'FTP_PERM_MASTER=elradfmw\nFTP_USER_DEFAULT=guest\n'
                    'FTP_PASSWORD_DEFAULT=guestpass\nFTP_PERM_DEFAULT=elr\n'
                    '[PATH]\nALLOWED_PATH=/tmp\n'
                    '[IP]\nIP_WHITELIST=127.0.0.1\nIP_BLACKLIST=192.168.0.1\n')
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = FTP_server.load_config()
    finally:
        os.chdir(cwd)
    assert result[0] == '127.0.0.1'
    assert result[1] == 2121
    assert result[11] is False
    assert result[12] == ''
    assert result[13] == ''
    assert result[14] == 100
    assert result[15] == 2
    assert result[16] == 60
    assert result[17] == 'DEBUG'


def test_upload_file(tmp_path):
    fake = FakeFTP()
    src = tmp_path / 'src.txt'
    src.write_text('data')
    assert FTP_Connection.upload_file(fake, str(src), 'dest.txt')
    assert fake.stored['dest.txt'] == b'data'


def test_download_file(tmp_path):
    fake = FakeFTP()
    fake.files['src.txt'] = b'download-data'
    assert FTP_Connection.download_file(fake, 'src.txt', str(tmp_path))
    output = (tmp_path / 'src.txt').read_bytes()
    assert output == b'download-data'
