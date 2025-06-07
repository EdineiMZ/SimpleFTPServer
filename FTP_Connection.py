import os
import logging
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ftplib import FTP
import threading

# Configuração do log
logging.basicConfig(level=logging.INFO, filename='ftp_client.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')


# Função para carregar as configurações de conexão do arquivo connections.ini
def load_ftp_config():
    config = configparser.ConfigParser()
    try:
        config.read('connections.ini')
        host = config.get('FTP', 'host')
        port = config.getint('FTP', 'port')
        user = config.get('FTP', 'user')
        password = config.get('FTP', 'password')
        return host, port, user, password
    except FileNotFoundError:
        messagebox.showerror("Erro", "Arquivo 'connections.ini' não encontrado.")
        logging.error("Arquivo 'connections.ini' não encontrado.")
        raise  # Re-raise a exceção para que o programa possa lidar com isso


# Popup de "Aguarde"
def show_wait_popup():
    wait_popup = tk.Toplevel()
    wait_popup.geometry("250x100")
    wait_popup.title("Aguarde")
    label_wait = tk.Label(wait_popup, text="Realizando operação...")
    label_wait.pack(pady=30)
    return wait_popup


# Função para realizar upload de arquivo
def upload_file(ftp, file_path, file_name):
    try:
        if not os.path.isfile(file_path):
            logging.error(f"Caminho inválido para upload: {file_path}")
            return False
        with open(file_path, 'rb') as file:
            ftp.storbinary(f"STOR {file_name}", file)
        logging.info(f"Upload do arquivo {file_name} concluído com sucesso")
        return True
    except Exception as e:
        logging.error(f"Erro durante upload de arquivo: {str(e)}")
        return False


# Função para realizar download de arquivo
def download_file(ftp, file_name, download_path):
    try:
        if not os.path.isdir(download_path):
            logging.error(f"Diretório de download inválido: {download_path}")
            return False
        safe_name = os.path.basename(file_name)
        local_file_path = os.path.join(download_path, safe_name)
        with open(local_file_path, 'wb') as file:
            ftp.retrbinary(f"RETR {file_name}", file.write)
        logging.info(f"Download do arquivo {file_name} concluído com sucesso")
        return True
    except Exception as e:
        logging.error(f"Erro durante download de arquivo: {str(e)}")
        return False


# Função para listar arquivos do servidor FTP
def list_files(ftp):
    try:
        files = ftp.nlst()
        logging.info(f"Arquivos no diretório do servidor FTP: {files}")
        return files
    except Exception as e:
        logging.error(f"Erro ao listar arquivos no servidor FTP: {str(e)}")
        return None


# Funções de interface gráfica
def perform_ftp_operation_with_feedback_and_wait_popup(operation_func, *args):
    wait_popup = show_wait_popup()
    try:
        host, port, user, password = load_ftp_config()
        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(user, password)

        operation_result = operation_func(ftp, *args)
        if operation_result:
            messagebox.showinfo("Sucesso", "Operação realizada com sucesso")
        else:
            messagebox.showerror("Erro", "Erro durante a operação")
    except Exception as e:
        logging.error(f"Erro ao conectar ao servidor FTP: {str(e)}")
        messagebox.showerror("Erro", f"Erro ao conectar ao servidor FTP: {str(e)}")
    finally:
        try:
            ftp.quit()
        except:
            pass
        wait_popup.destroy()


def upload():
    file_path = filedialog.askopenfilename(initialdir="/", title="Selecione o arquivo")
    if not file_path:
        return  # Cancelado pelo usuário

    file_name = os.path.basename(file_path)
    threading.Thread(target=perform_ftp_operation_with_feedback_and_wait_popup,
                     args=(upload_file, file_path, file_name)).start()


def download():
    try:
        host, port, user, password = load_ftp_config()
        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(user, password)

        files = list_files(ftp)
        if not files:
            messagebox.showerror("Erro", "Não foi possível listar arquivos no servidor FTP")
            return

        download_window = tk.Toplevel()
        download_window.geometry("300x150")
        download_window.title("Selecionar Arquivo para Download")

        label = tk.Label(download_window, text="Selecione o arquivo para download:")
        label.pack(pady=10)

        selected_file = tk.StringVar()
        selected_file.set(files[0] if files else "")  # Seleciona o primeiro arquivo por padrão
        dropdown = ttk.Combobox(download_window, textvariable=selected_file, values=files, state="readonly", width=30)
        dropdown.pack(pady=10)

        def start_download():
            file_name = selected_file.get()
            if not file_name:
                messagebox.showerror("Erro", "Nenhum arquivo selecionado")
                return

            download_path = filedialog.askdirectory(initialdir="/", title="Selecione onde salvar o arquivo")
            if not download_path:
                return  # Cancelado pelo usuário

            download_window.destroy()
            threading.Thread(
                target=perform_ftp_operation_with_feedback_and_wait_popup,
                args=(download_file, file_name, download_path)
            ).start()

        btn_download = tk.Button(download_window, text="Download", command=start_download)
        btn_download.pack(pady=10)

    except Exception as e:
        logging.error(f"Erro ao conectar ao servidor FTP: {str(e)}")
        messagebox.showerror("Erro", f"Erro ao conectar ao servidor FTP: {str(e)}")

    finally:
        try:
            ftp.quit()
        except:
            pass


# Funções de interface gráfica
def main():
    try:
        host, port, user, password = load_ftp_config()
    except FileNotFoundError:
        messagebox.showerror("Erro", "Arquivo 'connections.ini' não encontrado. O programa será encerrado.")
        return

    clienttk = tk.Tk()
    clienttk.title("Cliente FTP")
    clienttk.geometry("300x200")

    bt1 = tk.Button(clienttk, width=20, text="Upload de Arquivo", command=upload)
    bt1.place(x=50, y=50)

    bt2 = tk.Button(clienttk, width=20, text="Download de Arquivo", command=download)
    bt2.place(x=50, y=100)

    clienttk.mainloop()


if __name__ == '__main__':
    main()
