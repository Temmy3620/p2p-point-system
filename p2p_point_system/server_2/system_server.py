import signal
import sys
from core.server_core import ServerCore


my_p2p_server = None

def signal_handler(signal, frame):
    shutdown_server()

def shutdown_server():
    global my_p2p_server#関数の外の変数を使う
    my_p2p_server.shutdown()


def main(my_port, c_host, c_port, p_phrase):
    signal.signal(signal.SIGINT, signal_handler)#割り込みシグナルで、キーボードから「CTRL+C」で中断させる
    global my_p2p_server#関数の外の変数を使う
    my_p2p_server = ServerCore(my_port, c_host, c_port, p_phrase)#クラスからインスタンス作成
    my_p2p_server.start()#
    my_p2p_server.join_network()#

if __name__ == '__main__':

    args = sys.argv #コマンドライン引数使用
 
    if len(args) == 5:
        my_port = int(args[1]) #python スクリプト　args[1] args[2] args[3] args[4]
        c_host = args[2]
        c_port = int(args[3])
        p_phrase = args[4]
    else:
        print('Param Error')
        print('$ SmpleServer2.py <my_port> <core_node_ip_address> <core_node_port_num> <pass_phrase_for_keys>')
        quit()

    main(my_port, c_host, c_port, p_phrase)