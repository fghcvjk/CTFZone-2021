#!/usr/bin/env python3
import socket
import threading
import base64
import time
from secret import key, secret_message
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from secrets import token_bytes
TIMEOUT_PERIOD = 60*5
cipher_backend = default_backend()

(HOST, PORT) = ('0.0.0.0', 1337)


def makeMAC(data):
    if len(data) % 16 != 0:
        data += (16-len(data) % 16)*b'\x00'
    cipher = Cipher(algorithms.AES(key), modes.CBC(
        b'\x00'*16), backend=cipher_backend)
    encryptor = cipher.encryptor()
    all_encryption = encryptor.update(data)
    # print(all_encryption.hex())
    return all_encryption[-16:]


example_command = b"""t{from:"admin", to:"admin", amount:"1.0", comment:"i'm batman"}"""
starting_banner = """Banking System V0.1
You can transfer funds from your account to everyone else's.
Only people with more than 1000 credits get special treatment (admin is one of them).
Example of an authenticated command:
execute_command {0} {1}
""".format(base64.b64encode(example_command).decode('utf-8'), makeMAC(example_command).hex())
usage = b"""authenticate_command <base64(command)>
execute_command <base64(command)> <hex(tag)>
example command: %s
""" % example_command


def xor(a, b):
    return bytes([i ^ j for (i, j) in zip(a, b)])


def checkMAC(data, tag):
    return makeMAC(data) == tag


def show_funds(client_socket, accounts):
    money_list = b'Accounts:\n----------------\n'
    for key in accounts.keys():
        money_list += key.encode()+b'\t'+str(accounts[key]).encode()+b'\n'
    money_list += b'----------------\n'
    client_socket.sendall(money_list)
    if accounts['me'] > 1000.0:
        client_socket.sendall(b'Secret: '+secret_message+b'\n')


def parse_command(command):

    start = command.find(b't{')
    if start == -1:
        return None
    command = command[start+len(b't{'):]
    i = len(command)-1
    while i >= 0:
        if command[i] == 125:
            break
        i -= 1
    if i < 0:
        return None
    command = command[:i]
    parsed_command = {}
    for option in command.split(b','):
        option = option.strip()
        if option.find(b':') == -1:
            continue
        (option_type, option_value) = option.split(b':')
        option_type = option_type.strip()
        option_value = option_value.strip()
        if option_type not in [b"from", b"to", b"comment", b'amount']:
            continue
        if option_value[0] != 34 or option_value[-1] != 34:
            continue
        literal_option = option_value[1:-1]
        if option_type == b"from" or option_type == b"to" or option_type == b"comment":
            try:
                parsed_command[option_type.decode(
                    'utf-8')] = literal_option.decode('utf-8')
            except Exception:
                continue
        else:
            try:
                parsed_command[option_type.decode(
                    'utf-8')] = float(literal_option.decode('utf-8'))
            except Exception:
                continue

    return parsed_command


def authenticate_command(command, client_socket):
    parsed_command = parse_command(command)

    if (parsed_command == None) or ('from' not in parsed_command.keys()) or ('to' not in parsed_command.keys()) or ('amount' not in parsed_command.keys()):
        client_socket.sendall(b'Invalid command\n')
        return
    if parsed_command['from'] != 'me':
        client_socket.sendall(
            b"You can't authenticate withdrawing funds from another user's account!\n")
        return
    client_socket.sendall(b'MAC: '+makeMAC(command).hex().encode()+b'\n')


def execute_command(command, tag, client_socket, accounts):
    parsed_command = parse_command(command)
    if (parsed_command == None) or ('from' not in parsed_command.keys()) or ('to' not in parsed_command.keys()) or ('amount' not in parsed_command.keys()):
        client_socket.sendall(b'Invalid command\n')
        return accounts
    if checkMAC(command, tag):
        client_socket.sendall(b'Passed MAC check\n')
        users = accounts.keys()
        if (parsed_command['from'] not in users) or (parsed_command['to'] not in users):
            client_socket.sendall(b'Invalid user\n')
            return accounts
        if (accounts[parsed_command['from']] < parsed_command['amount']):
            client_socket.sendall(b'Not enough funds\n')
            return accounts
        accounts[parsed_command['from']
                 ] = accounts[parsed_command['from']]-parsed_command['amount']
        accounts[parsed_command['to']] = accounts[parsed_command['to']
                                                  ]+parsed_command['amount']
        if 'comment' in parsed_command.keys():
            client_socket.send(
                b'Comment:'+parsed_command['comment'].encode()+b'\n')
        client_socket.sendall(b'Transaction successful\n')
    else:
        client_socket.sendall(b'Wrong MAC\n')
    return accounts


def recv_until(client_socket, separator=b'\n', additional_data=b''):
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


def handle_connection(client_socket):
    accounts = {
        'admin': 1000000.0,
        'alice': 128.0,
        'bob': 42.3,
        'molly': 1337.0,
        'me': 1.0,
    }
    extra = b''
    client_socket.send(starting_banner.encode())
    initialTime = time.time()
    while True:
        show_funds(client_socket, accounts)
        if (time.time()-initialTime) > TIMEOUT_PERIOD:
            client_socket.sendall(b'Connection TIMEOUT')
            client_socket.close()
            return
        client_socket.sendall(b'>')

        (received_message, extra) = recv_until(
            client_socket, additional_data=extra)
        try:
            decoded = received_message.decode('utf-8')[:-1]
        except Exception:
            client_socket.send(b'Error decoding utf-8\n')
            continue

        if (decoded.find(' ') == -1) or ((decoded.split(' ')[0] != 'execute_command')and(decoded.split(' ')[0] != 'authenticate_command')):
            client_socket.send(usage)
            continue
        b64data = decoded.split(' ')[1]

        try:
            decodedData = base64.b64decode(b64data)
        except Exception:
            client_socket.send(b'Error decoding base64\n')
            continue
        if decoded.split(' ')[0] == 'execute_command':
            try:
                l = decoded.split(' ')[2]

                tag = bytes.fromhex(l)

            except Exception:
                client_socket.send(b'Error decoding tag\n')
                continue
            accounts = execute_command(
                decodedData, tag, client_socket, accounts)
        else:
            authenticate_command(decodedData, client_socket)


def start_server():
    basic_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    basic_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    basic_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    basic_socket.bind((HOST, PORT))
    basic_socket.listen()
    while True:
        (client_socket, address) = basic_socket.accept()
        try:
            threading.Thread(target=handle_connection,
                             args=(client_socket,)).start()
        except Exception:
            print('Lol, thread exited.')


if __name__ == "__main__":
    start_server()
