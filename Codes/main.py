import argparse
import json
import struct
from socket import *

neighbor_ip = {}  # store node name of neighbors and their ip address
neighbor_distance = {}  # store direct distances to neighbors
distance_output = {}  # store the DV and the next hop info
distance_update = 0  # whether the DV was updated or not. 1 for notifying neighbors. 0 for no changes


def _argparse():
    parser = argparse.ArgumentParser(description="This is description!")
    parser.add_argument('--node', action='store', required=True,
                        dest='node', help='node name')
    return parser.parse_args()


# make packages
def make_message(operation_code, node_name, distance_info):
    distance_vector = {}
    for key in distance_info:
        distance_vector[key] = distance_info[key]["distance"]
    format_data = json.dumps(distance_vector).encode()
    encode_data = struct.pack('!II', operation_code, ord(node_name)) + format_data
    return encode_data


# process the message, including update the distance vector
def process_message(node_name, msg):
    global distance_update
    neighbor_name = chr(struct.unpack('!I', msg[0:4])[0])
    distance_info_from_neighbor = json.loads(msg[4:].decode())
    for key in distance_info_from_neighbor:
        if key != node_name:
            if key not in distance_output or (
                    distance_output[key]["distance"] > distance_info_from_neighbor[key] + neighbor_distance[
                neighbor_name]):
                distance_output[key] = {
                    "distance": distance_info_from_neighbor[key] + neighbor_distance[neighbor_name],
                    "next_hop": neighbor_name}
                print("new route find")
                distance_update = 1


def main():
    counter = 0
    global distance_update
    parser = _argparse()
    node_name = parser.node
    # read and store ip info
    with open(node_name + '_ip.json', 'r') as json_data:
        ip_info = json.load(json_data, encoding='UTF-8')
        for key in ip_info:
            if key == node_name:
                node_ip = (ip_info[key][0], ip_info[key][1])
            else:
                neighbor_ip[key] = (ip_info[key][0], ip_info[key][1])
    # read and store distance info
    with open(node_name + '_distance.json', 'r') as json_data:
        distance_info = json.load(json_data, encoding='UTF-8')
        for key in distance_info:
            neighbor_distance[key] = distance_info[key]
            distance_output[key] = {"distance": distance_info[key], "next_hop": key}
    node_socket = socket(AF_INET, SOCK_DGRAM)
    node_socket.bind(node_ip)
    node_socket.settimeout(40)  # recvfrom method will only cause the program to be blocked for 40 seconds
    # greeting the neighbors
    for key in neighbor_ip:
        message = make_message(0, node_name, distance_output)
        node_socket.sendto(message, neighbor_ip[key])
    while True:
        try:
            msg, ip_address = node_socket.recvfrom(1024)
        except:
            # no update anymore, output the result
            with open(node_name + '_output.json', 'w') as json_data:
                json_data.write(json.dumps(distance_output, indent=4))
            break
        else:
            operation_code = struct.unpack('!I', msg[:4])[0]
            process_message(node_name, msg[4:])
            # notify neighbors of DV
            if distance_update == 1:
                for key in neighbor_ip:
                    node_socket.sendto(make_message(1, node_name, distance_output), neighbor_ip[key])
                distance_update = 0
            # just respond to greeting
            elif distance_update == 0 and operation_code == 0:
                node_socket.sendto(make_message(1, node_name, distance_output), ip_address)


if __name__ == '__main__':
    main()
