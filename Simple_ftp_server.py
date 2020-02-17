import socket               # Import socket module
import pickle
import sys
from collections import namedtuple
import random
import time

ACK_TYPE = 1010101010101010

data_pkt = namedtuple('data_pkt', 'seq_num checksum data_type data')
ack_pkt = namedtuple('ack_pkt', 'seq_num zero_field data_type')

ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)         
host = socket.gethostname()  
port = 62223

def calculate_checksum(message):
    checksum = 0
    for i in range(0, len(message), 2):
        my_message = str(message)
        w = ord(my_message[i]) + (ord(my_message[i+1]) << 8)
        checksum = checksum + w
        checksum = (checksum & 0xffff) + (checksum >> 16)
    return (not checksum) & 0xffff

def parse_command_line_arguments():
    port = sys.argv[1]
    file_name = sys.argv[2]
    prob = sys.argv[3]
    return int(port), file_name, float(prob)

def send_ack(seq_num):
    reply_message = [seq_num, "0000000000000000", "1010101010101010"]
    ack_socket.sendto(pickle.dumps(reply_message), (host, port))
    
def main():
    output_file="output.txt"
    port , file_name, prob_loss = parse_command_line_arguments()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)         
    host = socket.gethostname()  
    hostaddr = socket.gethostbyname(host)                
    s.bind((host, port))
    print_message = []
    packet_lost = False
    exp_seq_num = 0
    while True:
        data, addr = s.recvfrom(1000000)
        data = pickle.loads(data)
        seq_num, checksum, data_type, message = data[0], data[1], data[2], data[3]
        rand_loss = random.random()
        if rand_loss <= prob_loss:
            print("Packet loss, sequence number = ", seq_num)
            packet_lost = True
            exp_seq_num += 0
            
        else:
            if checksum != calculate_checksum(message):
                print("Packet dropped, checksum doesn't match!")
            if seq_num == exp_seq_num:
                ack_seq = int(seq_num)+1
                send_ack(ack_seq)
                print_message.append(seq_num)
                with open(output_file, 'ab') as file:
                    file.write(message)
                exp_seq_num += 1

if __name__ == "__main__":
    main()
