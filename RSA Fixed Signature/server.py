from support import recvUntil, startServer,sendMessage,sendUnicodeDecodeError
from support import sendWrongCommandError,sendGoodbye,sendHexDecodeError
from support import safeDecodeFromHex, setupLogging
from flag import flag
from Crypto.PublicKey import RSA
from Crypto.Util.number import bytes_to_long, long_to_bytes
import logging
import os
import socket

HOST="0.0.0.0"

PORT=1337

starting_banner="""Welcome to RSA unspecified parameter task
The server holds a signature of directive 'hello' and will only perform this directive.
Your goal is to make the server think that the signed directive is 'flag' instead
"""
help_info="""Available commands:
help - print this help
public - show initial modulus and exponent
signature - show signature
directive <directive> <exponent> <modulus>
quit - quit"""

prompt=">"

flag_found="I found 'flag' in your message for signing. Despicable..."

message_too_long='Message is too long to sign'

signature_too_long='Signature is too long'

signed_data="Signature: %s"

flag_message=f"Congratulations! Here is your flag: {flag}."

wrong_signature='Wrong signature'

unknown_directive='Unknown directive. Need hello or flag'

data_missing="Data missing"

need_integers="Modulus and exponent need to be integers"

def pad(msg):
    return b'\x00\x01'+bytes([0xff]*(256-len(msg)-3))+b'\x00'+msg

def unpad(padded_msg):
    if len(padded_msg)!=256:
        return None
    if padded_msg[:2]!=b'\x00\x01':
        return None
    padded_msg=padded_msg[2:]
    at_least_one=True
    while True:
        if len(padded_msg)==0:
            return None
        if padded_msg[0]==0xff:
            at_least_one==True
            padded_msg=padded_msg[1:]
        elif padded_msg[0]==0 and at_least_one:
            padded_msg=padded_msg[1:]
            break
        else:
            return None
    return padded_msg

def noFlag(message):
    return message.find(b'flag')==-1

def unrollSignature(e,n):
    global signature
    if (bytes_to_long(signature)>=n) or (n.bit_length()/bytes_to_long(signature).bit_length())>1.5:
        return None
    padded=long_to_bytes(pow(bytes_to_long(signature),e,n),256)
    return unpad(padded)

def sendSignature(client_socket):
    global signature
    sendMessage(client_socket,f'signature {signature.hex()}')

def sendPublicKey(client_socket,pk,n):
    sendMessage(client_socket,f'e{n}: {pk.e}\nN{n}: {pk.n}')

def handler(client_socket):
    """Main handler"""
    try:
        #Sending the starting banner and help information
        sendMessage(client_socket,starting_banner+help_info)
        additional_data_received=b''
        while True:
            #Sending prompt
            sendMessage(client_socket,prompt,True)
            #Receiving command from client
            (command,additional_data_received)=recvUntil(client_socket,additional_data=additional_data_received)
            try:
                #Decoding
                decoded_command=command.decode()
            except UnicodeDecodeError:
                logging.error('Error decoding command from client')
                sendUnicodeDecodeError(client_socket)
                continue 
            #Splitting into parts
            decoded_command=decoded_command.rstrip()
            command_parts=decoded_command.split(' ')
            actual_command=command_parts[0]


            #Checking the command
            if actual_command=='help':
                sendMessage(client_socket, help_info)

            elif actual_command=='quit':
                sendGoodbye(client_socket)
                break

            elif actual_command=='public':
                sendPublicKey(client_socket,pk,'')

            elif actual_command=='signature':
                sendSignature(client_socket)

            elif actual_command=='directive':
                if len(command_parts)<4:
                    sendMessage(client_socket,data_missing)
                    continue
                directive=command_parts[1]
                try:
                    modulus=int(command_parts[3])
                    exponent=int(command_parts[2])
                except ValueError:
                    sendMessage(client_socket,need_integers)
                    continue
                if directive!='hello' and directive!='flag':
                    sendMessage(client_socket,unknown_directive)
                    continue
                unrolled=unrollSignature(exponent,modulus) 
                if unrolled==None:
                    sendMessage(client_socket,wrong_signature)
                    continue
                if unrolled==directive.encode():
                    if directive=='hello':
                        sendMessage(client_socket,'Hello!')
                    elif directive=='flag':
                        sendMessage(client_socket,flag_message)
                    continue
            else:
                sendWrongCommandError(client_socket,actual_command)
        client_socket.close()
        logging.info('Closed connection')
    except socket.timeout:
        logging.info('Connection timed out')
        
if __name__=="__main__":
    setupLogging()
    global pk,signature
    if not os.path.isfile('private.pem'):
        logging.fatal('Private Key File not found. Aborting...')
        exit(0)
    with open('private.pem','rb') as f:
        pk_data=f.read()
    


    try:
        pk=RSA.importKey(pk_data)
    except ValueError:
        logging.fatal('Key data could not be parsed. Aborting...')
        exit(0)
    signature=long_to_bytes(pow(bytes_to_long(pad(b'hello')),pk.d,pk.n))
    startServer(HOST,PORT,handler)
