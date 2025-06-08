import os
import sys
# Ensure module import from repository root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import types
from configparser import ConfigParser

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
        self.dirs = {'/'}

    def storbinary(self, cmd, file, callback=None):
        filename = cmd.split()[1]
        data = file.read()
        self.stored[filename] = data
        if callback:
            callback(data)

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        filename = cmd.split()[1]
        data = self.files.get(filename)
        if data is None:
            raise Exception('missing file')
        callback(data)

    def nlst(self, path=None):
        path = path or '/'
        prefix = path.rstrip('/') + '/'
        result = []
        for p in self.dirs:
            if p.startswith(prefix) and p != prefix.rstrip('/'):
                name = p[len(prefix):].split('/')[0]
                if name not in result:
                    result.append(name)
        for f in self.files:
            if f.startswith(prefix):
                name = f[len(prefix):].split('/')[0]
                if name not in result:
                    result.append(name)
        return result

    def mkd(self, path):
        self.dirs.add(path)

    def mlsd(self, path, facts=None):
        prefix = path.rstrip('/') if path != '.' else ''
        if prefix:
            prefix += '/'
        for p in sorted(self.dirs.union(self.files)):
            if p.startswith(prefix) and p != prefix.rstrip('/'):
                name = p[len(prefix):].split('/')[0]
                full = prefix + name
                if full in self.dirs:
                    yield name, {'type': 'dir'}
                elif full in self.files:
                    yield name, {'type': 'file'}

    def size(self, filename):
        data = self.files.get(filename)
        return len(data) if data is not None else 0

def test_load_config(tmp_path):
    cfg = tmp_path / 'config.ini'
    cfg.write_text('[FTP_SERVER]\n'
                    'FTP_HOST=127.0.0.1\nFTP_PORT=2121\n'
                    'USE_TLS=False\n'
                    'MAX_CONNECTIONS=100\n'
                    'MAX_CONNECTIONS_PER_IP=2\n'
                    'TIMEOUT=60\n'
                    'LOG_LEVEL=DEBUG\n'
                    'ENCRYPTION_ENABLED=True\n'
                    'ENCRYPTION_KEY=mykey\n'
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
    assert result[18] is True
    assert result[19] == 'mykey'


def test_upload_file(tmp_path):
    fake = FakeFTP()
    src = tmp_path / 'src.txt'
    src.write_text('data')
    assert FTP_Connection.upload_file(fake, str(src), 'dest.txt', True, 'k', lambda *a: None)
    expected = FTP_Connection.xor_cipher(b'data', 'k')
    assert fake.stored['dest.txt'] == expected


def test_download_file(tmp_path):
    fake = FakeFTP()
    encrypted = FTP_Connection.xor_cipher(b'download-data', 'k')
    fake.files['src.txt'] = encrypted
    assert FTP_Connection.download_file(fake, 'src.txt', str(tmp_path), True, 'k', lambda *a: None)
    output = (tmp_path / 'src.txt').read_bytes()
    assert output == b'download-data'


def test_create_config_interactively(monkeypatch, tmp_path):
    responses = iter([
        '127.0.0.1',  # host
        '2121',        # port
        'master',      # master user
        'pass',        # master pass
        'guest',       # default user
        'guestpass',   # default pass
        '/tmp',        # allowed path
        '127.0.0.1',   # whitelist
        '',            # blacklist
        'n',           # tls
        '100',         # max connections
        '2',           # max per ip
        '60',          # timeout
        'DEBUG',       # log level
        'n',           # encryption
    ])

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('builtins.input', lambda _='': next(responses))

    FTP_server.create_config_interactively()

    cfg = ConfigParser()
    cfg.read(tmp_path / 'config.ini')

    assert cfg.get('FTP_SERVER', 'FTP_HOST') == '127.0.0.1'
    assert cfg.getint('FTP_SERVER', 'FTP_PORT') == 2121
    assert cfg.get('USERS', 'FTP_USER_MASTER') == 'master'


def test_upload_directory(tmp_path):
    fake = FakeFTP()
    src = tmp_path / 'srcdir'
    sub = src / 'sub'
    sub.mkdir(parents=True)
    (src / 'a.txt').write_text('1')
    (sub / 'b.txt').write_text('2')
    assert FTP_Connection.upload_directory(fake, str(src), '/dest', False, '', lambda *a: None)
    assert fake.stored['/dest/a.txt'] == b'1'
    assert fake.stored['/dest/sub/b.txt'] == b'2'


def test_download_directory(tmp_path):
    fake = FakeFTP()
    fake.dirs.update({'/folder', '/folder/sub'})
    fake.files['/folder/a.txt'] = b'1'
    fake.files['/folder/sub/b.txt'] = b'2'
    out = tmp_path / 'out'
    assert FTP_Connection.download_directory(fake, '/folder', str(out), False, '', lambda *a: None)
    assert (out / 'a.txt').read_text() == '1'
    assert (out / 'sub' / 'b.txt').read_text() == '2'
