import socket  # Import socket module
import sys
from collections import namedtuple
import pickle
import threading
import time
import select

DATA_TYPE = 0b101010101010101

data_pkt = namedtuple('data_pkt', 'seq_num checksum data_type data')
ack_pkt = namedtuple('ack_pkt', 'seq_num zero_field data_type')
N = 0  
MSS = 0 
ACK = 0 
num_pkts_sent = 0
num_pkts_acked = 0
seq_num = 0
window_low = 0
window_high = int(N)-1
total_pkts = 0
RTT = 0.06
pkts = []
done_transmitting = 0
starttime = 0
stoptime= 0

ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
host = socket.gethostname()
ack_port_num = 62223
ack_socket.bind((host, ack_port_num))

lock = threading.RLock()

def calculate_checksum(message):
    checksum = 0
    for i in range(0, len(message), 2):
        data = str(message)
        m = ord(data[i]) + (ord(data[i+1]) << 8)
        checksum = checksum + m
        checksum = (checksum & 0xffff) + (checksum >> 16)
    return (not checksum) & 0xfff



def fill_data(message, seq_num):
    pkt = data_pkt(seq_num, calculate_checksum(message), DATA_TYPE, message)
    packet_list = [pkt.seq_num, pkt.checksum, pkt.data_type, pkt.data]
    packed_pkt = pickle.dumps(packet_list)
    return packed_pkt


def fill_pkts(file_content, seq_num):
    pkts_to_send = []
    seq_num = 0
    for item in file_content:   
        pkts_to_send.append(fill_data(item, seq_num))
        seq_num += 1
    return pkts_to_send


def socket_send(pkts):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
    s.sendto(pkts, (host, port))
    s.close()

def sendFile(file_data, sock, hostname, port):
    global total_pkts
    total_pkts = len(file_data)
    print(total_pkts)
    global pkts
    global seq_num
    global RTT
    pkts= fill_pkts(file_data, seq_num)
    global num_pkts_sent
    current_max_window = min(int(N), int(total_pkts))
    while num_pkts_sent < current_max_window :
        if num_pkts_sent == 0:
            socket_send(pkts[num_pkts_sent])
            num_pkts_sent += 1
        else:
            break
       

def lsitenACK(sock, host, port):
    global window_high
    global window_low
    global num_pkts_sent
    global num_pkts_acked
    global total_pkts
    global ACK
    global done_transmitting
    global stoptime
    data = []
    done_transmitting = 0
    while True:
        ready = select.select([ack_socket], [], [], 2*RTT)
        if ready[0]:
            data = pickle.loads(ack_socket.recv(256))
            if data[2]=="1010101010101010":  
                ACK = data[0]
                if ACK:
                    lock.acquire()                    
                    if ACK > window_low and ACK <total_pkts:
                        temp_pckts_acked = ACK - window_low
                        old_window_high = window_high
                        window_high = min(window_high + temp_pckts_acked , total_pkts-1)
                        window_low = ACK
                        num_pkts_acked += temp_pckts_acked  
                        if (ACK >= old_window_high - N + 1) :
                            for i in range(int(N)):
                                if (window_low + i -1< int(total_pkts)):
                                    socket_send(pkts[window_low + i -1])
                                    if (num_pkts_sent == window_low + i) :
                                        num_pkts_sent = window_low + i
                                    
                    else:
                        if ACK == total_pkts:
                            print("Done!")
                            done_transmitting = 1
                            stoptime = time.time()
                            print("Running Time:",str(stoptime-starttime))
                            exit()

                    lock.release()
                                
        else:
            print("Timeout , sequence_num" + str(num_pkts_acked))
            data[0] = num_pkts_acked
            data[1] = ''
            data[2] = "1010101010101010"
            num_pkts_sent= window_low
            if data[2]=="1010101010101010": 
                ACK = data[0]
                if ACK:
                    lock.acquire()
                    if (ACK <= window_low and ACK <total_pkts) :
                        for i in range(int(N)) :
                            if ACK + i < total_pkts:
                                socket_send(pkts[ACK + i])
                                if (num_pkts_sent == ACK + i) :
                                    num_pkts_sent = ACK + i                                
                    lock.release()
        
                                    

def parse_command_line_arguments():
    host = sys.argv[1]
    port = sys.argv[2]
    file_name = sys.argv[3]
    my_window_size = sys.argv[4]
    my_mss = sys.argv[5]

    return host, int(port), file_name, int(my_window_size), int(my_mss)

def main():
    global N
    global MSS
    global starttime
    global port
    starttime = time.time()
    host, port, file, N, MSS = parse_command_line_arguments()
    global window_high
    window_high = int(N)-1
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
    
    try:
        file_data = []
        with open(file, 'rb') as f:
            while True:
                chunk = f.read(int(MSS)) 
                if chunk:
                    file_data.append(chunk)
                else:
                    break
    except:
        sys.exit("Failed to open file!")  
    sendFile(file_data, s, host, port)
    threading.Timer(2*RTT, lsitenACK, args=(s, host, port)).start()
    s.close()  


if __name__ == "__main__":
    main()
    
