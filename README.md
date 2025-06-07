# SimpleFTPServer
This project implements a simple FTP server and client with optional TLS and
file encryption.
- [x] Configurable TLS, logging and connection limits
- [x] Optional XOR-based encryption using a user-defined key
2. Run the client. If `connections.ini` is missing, a tutorial window will help
   you create it with the proper settings.
5. To enable file encryption, set `encryption_enabled` and `encryption_key` in both `connections.ini` and `config.ini`.
6. Configure the `config.ini` file to start up the server
   limits and log level.
2. Ensure the dependencies are installed (`pyftpdlib`).
3. Run the server with `python FTP_server.py`.

## Features
- [x] FTP Server
- [x] FTP Client
- [x] FTP Server and Client with GUI, multithreading and file upload/download

## How to use
1. Run the server
2. Run the client
3. Connect to the server
4. Use the client to upload and download files -- configure the connection settings in the connections.ini. The client defaults to connecting to `127.0.0.1` unless you override `host` in that file.
5. To use the FTP server, you need to configure the config.ini to start up the server

## How to run the server
1. Configure the config.ini file to set the server's IP and port
2. Ensure the dependencies are installed (pyftpdlib)
3. Run the server with `python FTP_server.py`

=======
FTP Server
