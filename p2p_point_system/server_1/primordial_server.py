import signal
import sys

from core.server_core import ServerCore

my_p2p_server = None


def signal_handler(signal, frame):
    shutdown_server()

def shutdown_server():
    global my_p2p_server#関数の外の変数を使う
    my_p2p_server.shutdown()


def main(my_port, p_phrase):
    signal.signal(signal.SIGINT, signal_handler)#割り込みシグナルで、キーボードから「CTRL+C」で中断させる
    global my_p2p_server#関数の外の変数を使う
    # 始原のCoreノードとして起動する
    my_p2p_server = ServerCore(my_port, None, None, p_phrase)#server_coreを起動して、各オブジェクトを確立する
    my_p2p_server.start()#


if __name__ == '__main__':

    args = sys.argv #コマンドライン引数を使用
 
    if len(args) == 3:
        my_port = int(args[1]) #~$python スクリプト args[1] args[2]
        p_phrase = args[2]
    else:
        print('Param Error')
        print('$ SmpleServer1.py <my_port> <pass_phrase_for_keys>')
        quit()

    main(my_port, p_phrase)