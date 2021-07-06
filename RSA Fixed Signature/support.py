import socket
import threading
import logging
class ErrorParsingCommand(Exception):
    pass
class NoSuchCommand(Exception):
    pass
class WrongNumberOfArguments(Exception):
    pass
DEFAULT_SOCKET_TIMEOUT=20*60
UNICODE_DECODING_ERROR_MESSAGE='There was and error decoding your message as Unicode'
HEX_DECODING_ERROR_MESSAGE='There was and error decoding the hexadecimal encoding in your message'
WRONG_COMMAND_ERROR_MESSAGE='Wrong command: %s'
GOODBYE_MESSAGE='Goodbye!'
def setupLogging():
    LOG_FILENAME='server.log'
    LOG_FORMAT='%(levelname)s %(asctime)s %(message)s'
    logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO,format=LOG_FORMAT)
def safeDecodeFromHex(hex_message):
    try:
        decoded=bytes.fromhex(hex_message)
    except ValueError:
        return None
    return decoded

def sendMessage(client_socket, message,without_newline=False):
    client_socket.sendall((message+('\n' if not without_newline else '')).encode())

def sendUnicodeDecodeError(client_socket):
    send_message(client_socket,UNICODE_DECODING_ERROR_MESSAGE)

def sendHexDecodeError(client_socket):
    sendMessage(client_socket,HEX_DECODING_ERROR_MESSAGE)
def sendWrongCommandError(client_socket,command):
    sendMessage(client_socket,WRONG_COMMAND_ERROR_MESSAGE%command)

def sendGoodbye(client_socket):
    sendMessage(client_socket,GOODBYE_MESSAGE)



def recvUntil(client_socket, separator=b'\n', additional_data=b''):
    """
    Receive data from socket until a given separator. Any additional data received after a separator is given back.
    """ 
    all_data = additional_data
    sep_index = all_data.find(separator)
    if sep_index != -1:

        additional_data = all_data[sep_index+1:]

        return (all_data[:sep_index+1], additional_data)
    additional_data = b''
    while True:
        cur_data = client_socket.recv(1024)
        if len(cur_data) == 0:
            break
        sep_index = cur_data.find(separator)
        if sep_index != -1:
            all_data += cur_data[:sep_index+1]
            additional_data = cur_data[sep_index+1:]
            break
        all_data += cur_data
    return (all_data, additional_data)

def startServer(HOST,PORT,handleConnection):
    basic_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    basic_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    basic_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    basic_socket.bind((HOST, PORT))
    basic_socket.listen()
    logging.info(f'Started server on: {HOST}:{PORT}')
    while True:
        (client_socket, address) = basic_socket.accept()
        logging.info(f'Client from address {address} connected')
        client_socket.settimeout(DEFAULT_SOCKET_TIMEOUT)
        try:
            threading.Thread(target=handleConnection,
                             args=(client_socket,)).start()
        except KeyboardInterrupt:
            return
        except Exception as e:
            logging.error(f'Caught exception: {repr(e)}')


