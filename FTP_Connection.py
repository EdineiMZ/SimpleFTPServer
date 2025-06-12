import os
import logging
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ftplib import FTP
import threading
import io
import time

FIRST_RUN_FILE = 'connections.ini'

# Configuração do log
logging.basicConfig(
    level=logging.INFO,
    filename='ftp_client.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console)

logger = logging.getLogger(__name__)


def xor_cipher(data: bytes, key: str) -> bytes:
    """Encrypt or decrypt data using a simple XOR cipher."""
    if not key:
        return data
    key_bytes = key.encode('utf-8')
    return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))


# Função para carregar as configurações de conexão do arquivo connections.ini
def load_ftp_config():
    config = configparser.ConfigParser()
    try:
        config.read('connections.ini')
        host = config.get('FTP', 'host')
        port = config.getint('FTP', 'port')
        user = config.get('FTP', 'user')
        password = config.get('FTP', 'password')
        encryption_enabled = config.getboolean('FTP', 'encryption_enabled', fallback=False)
        encryption_key = config.get('FTP', 'encryption_key', fallback='')
        return host, port, user, password, encryption_enabled, encryption_key
    except FileNotFoundError:
        messagebox.showerror("Erro", "Arquivo 'connections.ini' não encontrado.")
        logger.error("Arquivo 'connections.ini' não encontrado.")
        raise  # Re-raise a exceção para que o programa possa lidar com isso


def first_time_tutorial():
    """Display a simple GUI to create the connections.ini file."""
    tutorial = tk.Tk()
    tutorial.title("Configuração Inicial")
    tutorial.geometry("300x260")

    host_var = tk.StringVar()
    port_var = tk.StringVar(value="21")
    user_var = tk.StringVar()
    pass_var = tk.StringVar()
    enc_var = tk.BooleanVar()
    key_var = tk.StringVar()

    ttk.Label(tutorial, text="Host:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(tutorial, textvariable=host_var).grid(row=0, column=1, padx=5)

    ttk.Label(tutorial, text="Porta:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(tutorial, textvariable=port_var).grid(row=1, column=1, padx=5)

    ttk.Label(tutorial, text="Usuário:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(tutorial, textvariable=user_var).grid(row=2, column=1, padx=5)

    ttk.Label(tutorial, text="Senha:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(tutorial, textvariable=pass_var, show="*").grid(row=3, column=1, padx=5)

    ttk.Checkbutton(tutorial, text="Habilitar criptografia", variable=enc_var).grid(row=4, column=0, columnspan=2, pady=5)

    ttk.Label(tutorial, text="Chave de criptografia:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(tutorial, textvariable=key_var).grid(row=5, column=1, padx=5)

    def save():
        config = configparser.ConfigParser()
        config['FTP'] = {
            'host': host_var.get(),
            'port': port_var.get(),
            'user': user_var.get(),
            'password': pass_var.get(),
            'encryption_enabled': str(enc_var.get()),
            'encryption_key': key_var.get(),
        }
        with open(FIRST_RUN_FILE, 'w') as f:
            config.write(f)
        messagebox.showinfo("Configurações", "Arquivo connections.ini criado")
        tutorial.destroy()

    ttk.Button(tutorial, text="Salvar", command=save).grid(row=6, column=0, columnspan=2, pady=10)

    tutorial.mainloop()


# Popup de "Aguarde"
def show_wait_popup():
    wait_popup = tk.Toplevel()
    wait_popup.geometry("250x100")
    wait_popup.title("Aguarde")
    label_wait = tk.Label(wait_popup, text="Realizando operação...")
    label_wait.pack(pady=30)
    return wait_popup


# Função para realizar upload de arquivo
def upload_file(
    ftp,
    file_path,
    file_name,
    encryption_enabled=False,
    key='',
    progress_callback=None,
):
    try:
        if not os.path.isfile(file_path):
            logger.error(f"Caminho inválido para upload: {file_path}")
            return False

        start = time.perf_counter()
        if encryption_enabled:
            with open(file_path, 'rb') as file:
                data = xor_cipher(file.read(), key)
            ftp.storbinary(
                f"STOR {file_name}",
                io.BytesIO(data),
                callback=(lambda d: progress_callback(len(d), len(data)) if progress_callback else None),
            )
        else:
            total = os.path.getsize(file_path)
            sent = 0

            def cb(data):
                nonlocal sent
                sent += len(data)
                if progress_callback:
                    progress_callback(sent, total)

            with open(file_path, 'rb') as file:
                ftp.storbinary(f"STOR {file_name}", file, callback=cb)
        elapsed = time.perf_counter() - start
        logger.info(f"Upload do arquivo {file_name} concluído em {elapsed:.2f}s")
        return True
    except Exception as e:
        logger.error(f"Erro durante upload de arquivo: {str(e)}")
        return False


# Função para realizar download de arquivo
def download_file(
    ftp,
    file_name,
    download_path,
    encryption_enabled=False,
    key='',
    progress_callback=None,
):
    try:
        if not os.path.isdir(download_path):
            logger.error(f"Diretório de download inválido: {download_path}")
            return False
        safe_name = os.path.basename(file_name)
        local_file_path = os.path.join(download_path, safe_name)

        start = time.perf_counter()
        size = ftp.size(file_name) or 0
        received = 0

        def cb(data):
            nonlocal received
            received += len(data)
            if progress_callback:
                progress_callback(received, size)

        if encryption_enabled:
            buffer = io.BytesIO()

            def write_and_update(data):
                cb(data)
                buffer.write(data)

            ftp.retrbinary(f"RETR {file_name}", write_and_update)
            data = xor_cipher(buffer.getvalue(), key)
            with open(local_file_path, 'wb') as file:
                file.write(data)
        else:
            with open(local_file_path, 'wb') as file:
                def write_and_update(data):
                    cb(data)
                    file.write(data)

                ftp.retrbinary(f"RETR {file_name}", write_and_update)
        elapsed = time.perf_counter() - start
        logger.info(f"Download do arquivo {file_name} concluído em {elapsed:.2f}s")
        return True
    except Exception as e:
        logger.error(f"Erro durante download de arquivo: {str(e)}")
        return False


# Função para realizar upload de diretório
def upload_directory(
    ftp,
    dir_path,
    remote_dir='.',
    encryption_enabled=False,
    key='',
    progress_callback=None,
):
    try:
        if not os.path.isdir(dir_path):
            logger.error(f"Diretório inválido para upload: {dir_path}")
            return False

        for root, _, files in os.walk(dir_path):
            rel = os.path.relpath(root, dir_path)
            target = os.path.join(remote_dir, rel).replace('\\', '/') if rel != '.' else remote_dir.rstrip('/')
            if rel != '.':
                try:
                    ftp.mkd(target)
                except Exception:
                    pass
            for name in files:
                local_file = os.path.join(root, name)
                remote_file = os.path.join(target, name).replace('\\', '/')
                if not upload_file(
                    ftp,
                    local_file,
                    remote_file,
                    encryption_enabled,
                    key,
                    progress_callback,
                ):
                    return False
        return True
    except Exception as e:
        logger.error(f"Erro durante upload de pasta: {str(e)}")
        return False


# Função para realizar download de diretório
def download_directory(
    ftp,
    remote_dir,
    local_path,
    encryption_enabled=False,
    key='',
    progress_callback=None,
):
    try:
        os.makedirs(local_path, exist_ok=True)
        for name, facts in ftp.mlsd(remote_dir, facts=['type']):
            if name in {'.', '..'}:
                continue
            remote_item = f"{remote_dir.rstrip('/')}/{name}"
            if facts.get('type') == 'dir':
                download_directory(
                    ftp,
                    remote_item,
                    os.path.join(local_path, name),
                    encryption_enabled,
                    key,
                    progress_callback,
                )
            else:
                download_file(
                    ftp,
                    remote_item,
                    local_path,
                    encryption_enabled,
                    key,
                    progress_callback,
                )
        return True
    except Exception as e:
        logger.error(f"Erro durante download de pasta: {str(e)}")
        return False


# Função para listar arquivos do servidor FTP
def list_files(ftp):
    try:
        files = ftp.nlst()
        logger.info(f"Arquivos no diretório do servidor FTP: {files}")
        return files
    except Exception as e:
        logger.error(f"Erro ao listar arquivos no servidor FTP: {str(e)}")
        return None


# Funções de interface gráfica
def perform_ftp_operation_with_progress(title, operation_func, *args):
    progress_win = tk.Toplevel()
    progress_win.title(title)
    progress_win.geometry("300x100")
    bar = ttk.Progressbar(progress_win, orient="horizontal", length=250, mode="determinate")
    bar.pack(pady=20)

    def update(curr, total):
        bar["maximum"] = total if total else 1
        bar["value"] = curr
        progress_win.update_idletasks()

    try:
        host, port, user, password, enc_enabled, enc_key = load_ftp_config()
        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(user, password)

        operation_result = operation_func(
            ftp,
            *args,
            encryption_enabled=enc_enabled,
            key=enc_key,
            progress_callback=update,
        )
        if operation_result:
            messagebox.showinfo("Sucesso", "Operação realizada com sucesso")
        else:
            messagebox.showerror("Erro", "Erro durante a operação")
    except Exception as e:
        logger.error(f"Erro ao conectar ao servidor FTP: {str(e)}")
        messagebox.showerror("Erro", f"Erro ao conectar ao servidor FTP: {str(e)}")
    finally:
        try:
            ftp.quit()
        except Exception:
            pass
        progress_win.destroy()


def upload():
    file_paths = filedialog.askopenfilenames(initialdir="/", title="Selecione os arquivos")
    if not file_paths:
        return

    for path in file_paths:
        name = os.path.basename(path)
        threading.Thread(
            target=perform_ftp_operation_with_progress,
            args=(f"Upload {name}", upload_file, path, name),
        ).start()


def download():
    try:
        host, port, user, password, _, _ = load_ftp_config()
        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(user, password)

        files = list_files(ftp)
        if not files:
            messagebox.showerror("Erro", "Não foi possível listar arquivos no servidor FTP")
            return

        download_window = tk.Toplevel()
        download_window.geometry("300x250")
        download_window.title("Selecionar Arquivos para Download")

        label = tk.Label(download_window, text="Selecione os arquivos para download:")
        label.pack(pady=10)

        listbox = tk.Listbox(download_window, selectmode=tk.MULTIPLE, width=40, height=8)
        for f in files:
            listbox.insert(tk.END, f)
        listbox.pack(pady=10)

        def start_download():
            choices = [listbox.get(i) for i in listbox.curselection()]
            if not choices:
                messagebox.showerror("Erro", "Nenhum arquivo selecionado")
                return

            download_path = filedialog.askdirectory(initialdir="/", title="Selecione onde salvar os arquivos")
            if not download_path:
                return

            download_window.destroy()
            for choice in choices:
                threading.Thread(
                    target=perform_ftp_operation_with_progress,
                    args=(f"Download {choice}", download_file, choice, download_path)
                ).start()

        btn_download = tk.Button(download_window, text="Download", command=start_download)
        btn_download.pack(pady=10)

    except Exception as e:
        logger.error(f"Erro ao conectar ao servidor FTP: {str(e)}")
        messagebox.showerror("Erro", f"Erro ao conectar ao servidor FTP: {str(e)}")

    finally:
        try:
            ftp.quit()
        except:
            pass


# Funções de interface gráfica
def main_tk():
    if not os.path.exists(FIRST_RUN_FILE):
        first_time_tutorial()

    try:
        host, port, user, password, _, _ = load_ftp_config()
    except FileNotFoundError:
        messagebox.showerror("Erro", "Arquivo 'connections.ini' não encontrado. O programa será encerrado.")
        return

    clienttk = tk.Tk()
    clienttk.title("Cliente FTP")
    clienttk.geometry("300x200")

    bt_conf = tk.Button(clienttk, width=20, text="Configurações", command=first_time_tutorial)
    bt_conf.place(x=50, y=20)

    bt1 = tk.Button(clienttk, width=20, text="Upload de Arquivo", command=upload)
    bt1.place(x=50, y=60)

    bt2 = tk.Button(clienttk, width=20, text="Download de Arquivo", command=download)
    bt2.place(x=50, y=100)

    clienttk.mainloop()


def main():
    try:
        from PyQt5 import QtWidgets  # type: ignore
    except Exception:
        logger.warning('PyQt5 não encontrado, usando interface Tkinter')
        main_tk()
        return

    from client_pyqt import main as qt_main

    qt_main()


if __name__ == '__main__':
    main()
