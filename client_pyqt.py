# PyQt5 interface for SimpleFTPServer client
import os
import threading
from ftplib import FTP
from PyQt5 import QtWidgets

from FTP_Connection import (
    upload_file,
    download_file,
    upload_directory,
    download_directory,
    list_files,
    load_ftp_config,
    first_time_tutorial,
)


def main():
    class MainWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('Cliente FTP')
            layout = QtWidgets.QVBoxLayout(self)
            self.btn_conf = QtWidgets.QPushButton('Configurações')
            self.btn_up_file = QtWidgets.QPushButton('Upload de Arquivos')
            self.btn_up_dir = QtWidgets.QPushButton('Upload de Pasta')
            self.btn_down_file = QtWidgets.QPushButton('Download de Arquivos')
            self.btn_down_dir = QtWidgets.QPushButton('Download de Pasta')
            for b in [
                self.btn_conf,
                self.btn_up_file,
                self.btn_up_dir,
                self.btn_down_file,
                self.btn_down_dir,
            ]:
                layout.addWidget(b)

            self.btn_conf.clicked.connect(first_time_tutorial)
            self.btn_up_file.clicked.connect(self.upload_files)
            self.btn_up_dir.clicked.connect(self.upload_dir)
            self.btn_down_file.clicked.connect(self.download_files)
            self.btn_down_dir.clicked.connect(self.download_dir)

        def connect_ftp(self):
            host, port, user, password, enc, key = load_ftp_config()
            ftp = FTP()
            ftp.connect(host, port)
            ftp.login(user, password)
            return ftp, enc, key

        def run_with_progress(self, title, func, *args):
            progress = QtWidgets.QProgressDialog(title, 'Cancelar', 0, 100, self)
            progress.setWindowTitle(title)
            progress.setAutoClose(True)
            progress.show()

            def update(curr, total):
                progress.setMaximum(total if total else 1)
                progress.setValue(curr)

            def work():
                try:
                    ftp, enc, key = self.connect_ftp()
                    func(
                        ftp,
                        *args,
                        encryption_enabled=enc,
                        key=key,
                        progress_callback=update,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, 'Erro', str(e))
                finally:
                    try:
                        ftp.quit()
                    except Exception:
                        pass
                    progress.close()

            threading.Thread(target=work).start()

        def upload_files(self):
            paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
                self, 'Selecione os arquivos'
            )
            for path in paths:
                name = os.path.basename(path)
                self.run_with_progress(f'Upload {name}', upload_file, path, name)

        def upload_dir(self):
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self, 'Selecione a pasta'
            )
            if directory:
                remote, ok = QtWidgets.QInputDialog.getText(
                    self, 'Destino', 'Pasta no servidor:', text='.'
                )
                if ok:
                    self.run_with_progress(
                        'Upload de Pasta', upload_directory, directory, remote
                    )

        def download_files(self):
            try:
                ftp, enc, key = self.connect_ftp()
                files = list_files(ftp)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, 'Erro', str(e))
                return
            if not files:
                QtWidgets.QMessageBox.critical(self, 'Erro', 'Nenhum arquivo disponível')
                return
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle('Selecionar Arquivos')
            vbox = QtWidgets.QVBoxLayout(dialog)
            listw = QtWidgets.QListWidget()
            listw.addItems(files)
            listw.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
            vbox.addWidget(listw)
            btn = QtWidgets.QPushButton('OK')
            vbox.addWidget(btn)
            btn.clicked.connect(dialog.accept)
            if not dialog.exec_():
                ftp.quit()
                return
            choices = [item.text() for item in listw.selectedItems()]
            save = QtWidgets.QFileDialog.getExistingDirectory(self, 'Salvar em')
            ftp.quit()
            if not save or not choices:
                return
            for c in choices:
                self.run_with_progress(f'Download {c}', download_file, c, save)

        def download_dir(self):
            remote, ok = QtWidgets.QInputDialog.getText(
                self, 'Pasta remota', 'Caminho no servidor:', text='.'
            )
            if not ok:
                return
            local = QtWidgets.QFileDialog.getExistingDirectory(self, 'Salvar em')
            if not local:
                return
            self.run_with_progress('Download de Pasta', download_directory, remote, local)

    app = QtWidgets.QApplication([])
    win = MainWindow()
    win.show()
    app.exec_()


if __name__ == '__main__':
    main()
