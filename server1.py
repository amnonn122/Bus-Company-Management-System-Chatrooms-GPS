import socket
import urllib.request
import time
from _thread import *
import random
import os

# change to your real IP  address
HOST = "127.0.0.1"

def internet_on():
    """function checks if Internet is on"""
    try:
        urllib.request.urlopen('http://216.58.192.142', timeout=1)
        return True
    except:
        return False


PORT = 8888

# list of all the connections that connected to the server
all_connections = []

# keys: worker number , values:[connection, IP address]
all_addresses_wmnumber = {}

# list of all the managers that connected to the server
all_managers = []


# setting up the workers numbers from the .txt files
def setting_up_workers_numbers():
    diver_file = open('drivers.txt', 'r')
    manager_file = open('managers.txt', 'r')

    diver_file_string = diver_file.read()
    manager_file_string = manager_file.read()

    diver_file.close()
    manager_file.close()

    global driver_Numbers, manager_Numbers

    driver_Numbers = diver_file_string.split('\n')
    manager_Numbers = manager_file_string.split('\n')


# create the socket - start the server
def socket_create():
    try:
        global s

        s = socket.socket()

    except socket.error as msg:
        print("socket error: " + str(msg))


# binding
def socket_bind():
    for c in all_connections:
        c.close()

    del all_connections[:]
    all_addresses_wmnumber.clear()

    try:
        print("Binding socket to port: " + str(PORT))
        s.bind((HOST, PORT))
        s.listen(5)
    except socket.error as msg:
        print("binding error: " + str(msg) + "\n" + "retrying again..")
        time.sleep(5)
        socket_bind()


# accept each connection and start threading
def accept_connections():
    while True:
        try:
            global conn, addr
            conn, addr = s.accept()

            all_connections.append(conn)
            print("Connected with " + addr[0] + ":" + str(addr[1]))

            start_new_thread(handle_client, (conn,))
            start_new_thread(checking_socket_status, ())

        except:
            print("Error accepting connections")


# The program always runs in the background and checks whether the customer is connected or not.
# if not the function deletes the client from the list of connected customers (all_addresses_wmnumber)
def checking_socket_status():
    while True:
        try:
            for i in all_addresses_wmnumber:
                try:
                    all_addresses_wmnumber[i][0].sendall("".encode('utf-8'))
                except:
                    del all_addresses_wmnumber[i]
        except:
            pass


# This function always works in the background and handles all information that comes from customers
# and runs other functions according to information received from the customer.
def handle_client(conn):
    while True:
        try:
            data = conn.recv(1024)
            data_decoded = data.decode()
            data_splited = data_decoded.split(' ')

            if data_decoded[:6] == 'Number':
                first_connect_from_manager(data_splited)
            elif data_decoded[:5] == 'Route':
                route_send(data_splited, data_decoded)
            elif data_decoded[:5] == 'ROUTE':
                worker_number = data_splited[-1]
                send_to_random_manager(data, worker_number)
            elif data_decoded[:5] == 'CLOSE':
                worker_number = data_splited[4]
                send_to_all(data, worker_number)
                del all_addresses_wmnumber[worker_number]
            else:
                worker_number = data_splited[1]
                send_to_all(data, worker_number)
        except:
            pass


# When a new client connects to the system, this function checks whether the driver is already connected or not.
# In addition, the function adds the client who joined the workers dictionary - all_addresses_wmnumber.
def first_connect_from_manager(data_splited):
    number = data_splited[2]
    worker_type = data_splited[1]
    if worker_type == 'M':
        if exist(number):
            conn.send('False'.encode('utf-8'))
        else:
            b = False
            for i in manager_Numbers:
                if i == number and not b:
                    b = True
                    all_addresses_wmnumber[number] = [conn, addr[0]]
                    all_managers.append(number)
                    conn.sendall('True'.encode('utf-8'))
                    break
            if not b:
                conn.send('False'.encode('utf-8'))
    else:
        if exist(number):
            conn.send('False'.encode('utf-8'))
        else:
            b = False
            for i in driver_Numbers:
                if i == number and not b:
                    b = True
                    all_addresses_wmnumber[number] = [conn, addr[0]]
                    conn.sendall('True'.encode('utf-8'))
                    break
            if not b:
                conn.send('False'.encode('utf-8'))


# func for first_connect_from_manager func
# The func receives the workers number
def exist(n):
    numbers = all_addresses_wmnumber.keys()
    for i in numbers:
        if n == i:
            return True
    return False


# When a driver requests a line,
# this function sends the request to a random scheduler that is connected to the system.
# The func receives the driver's number
def send_to_random_manager(data, worker_number):
    conn_worker = all_addresses_wmnumber[worker_number][0]
    if is_manager_connected():
        conn_worker.send('MANNAGER IS CONNECTED'.encode('utf-8'))
        random_mannager = random.choice(all_managers)
        while not exist(random_mannager):
            random_mannager = random.choice(all_managers)
        random_mannager_contact = all_addresses_wmnumber[random_mannager]
        random_mannager_contact[0].sendall(data)
    else:
        conn_worker.send('MANNAGER NOT CONNECTED'.encode('utf-8'))


# A function that checks whether there are connected managers
def is_manager_connected():
    numbers = all_addresses_wmnumber.keys()
    for i in numbers:
        if int(i) < 1000:
            return True
    return False


# The function sends the data to all the clients connected to the server
# except for the employee number that was received as a function variable (worker_number).
def send_to_all(data, worker_number):
    conn_worker = all_addresses_wmnumber[str(worker_number)][0]
    for i, conn1 in enumerate(all_connections):
        if conn1 != conn_worker:
            try:
                all_connections[i].sendall(data)
                #print(data, worker_number, conn_worker, conn1)
            except:
                all_connections.remove(all_connections[i])


# data_decoded will be in this form: "Route _drivernumber_ _routenumber_ _busnumber_ _hour_"
# data_splited will be data_decoded.split(' ')
# The function sends all the coordinates of the line that the manager requested send to the driver.
def route_send(data_splited, data_decoded):
    try:
        driver = all_addresses_wmnumber[data_splited[1]]
        conn_driver = driver[0]
        route_number_splited = data_splited[2].split('-')
        path = 'route\\' + route_number_splited[0] + "\\" + route_number_splited[1] + "-" + route_number_splited[
            2] + '.txt'
        with open(path, 'r') as coordinates_file:
            to_send = data_decoded + "\n"
            coordinates_file_string = coordinates_file.read()
            coordinates_file.close()
            to_send += coordinates_file_string
        conn_driver.sendall(to_send.encode('utf-8'))
    except Exception as e:
        print(e)


def main():
    if HOST != "127.0.0.1" and internet_on():
        print("you are connected to internet")
        setting_up_workers_numbers()
        socket_create()
        socket_bind()
        accept_connections()
    elif HOST == "127.0.0.1":
        setting_up_workers_numbers()
        socket_create()
        socket_bind()
        accept_connections()
    else:
        print("Erorr")


if __name__ == '__main__':
    main()
