import socket
from statistics import mode
import threading
import json
import pickle
import time
import copy
import  os

from blockchain.blockchain_manager import BlockchainManager
from blockchain.block_builder import BlockBuilder
from transaction.transaction_pool import TransactionPool
from transaction.utxo_manager import UTXOManager
from transaction.transactions import CoinbaseTransaction
from utils.key_manager import KeyManager
from utils.rsa_util import RSAUtil
from p2p.my_protocol_message_store import MessageStore
from p2p.connection_manager import ConnectionManager
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
from p2p.message_manager import (
    MSG_NEW_TRANSACTION,
    MSG_NEW_BLOCK,
    MSG_REQUEST_FULL_CHAIN,
    RSP_FULL_CHAIN,
    MSG_ENHANCED,
)


STATE_INIT = 0
STATE_STANDBY = 1
STATE_CONNECTED_TO_CENTRAL = 3
STATE_SHUTTING_DOWN = 3

# TransactionPoolの確認頻度
# 動作チェック用に数字小さくしてるけど、600(10分)くらいはあって良さそ
CHECK_INTERVAL = 10

b_path = "s_blockchain" #blockchainが格納されるbainyファイル
h_path = "prev_blockhash"

class ServerCore:

    def __init__(self, my_port = 50082, core_node_host=None, core_node_port=None, pass_phrase=None):
        self.server_state = STATE_INIT
        print('Initializing server...')
        self.my_ip = self.__get_myip() #ローカルIPアドレスの取得
        print('Server IP address is set to ... ', self.my_ip)
        self.my_port = my_port
        self.cm = ConnectionManager(self.my_ip, self.my_port, self.__handle_message)#connecttionManagerから
        self.mpmh = MyProtocolMessageHandler()
        self.core_node_host = core_node_host#接続するネットワークのIPアドレス
        self.core_node_port = core_node_port#接続するcoreのポート番号指定
        self.bb = BlockBuilder()
        my_genesis_block = self.bb.generate_genesis_block()
        self.bm = BlockchainManager(my_genesis_block.to_dict())
        self.prev_block_hash = self.bm.get_hash(my_genesis_block.to_dict())
        self.tp = TransactionPool()
        self.is_bb_running = False
        self.flag_stop_block_build = False
        self.mpm_store = MessageStore()
        self.km = KeyManager(None, pass_phrase)
        self.rsa_util = RSAUtil()
        self.um = UTXOManager(self.km.my_address())
        

        """
        自作エリア-start
        """
        if os.stat(b_path).st_size != 0:#blockchainファイルが空ではない時
            if os.stat(h_path).st_size != 0:#hashファイルが空ではない時
                print("savefile exists.....")
                with open(b_path, "rb") as f:
                    self.bm.chain = pickle.load(f)#ファイルを読み込む
                with open(h_path, "rb") as f:
                    self.prev_block_hash = pickle.load(f)#ファイルを読み込む
        """
        自作エリア-end
        """
            

    def start_block_building(self):
        '''
        transactionpoolにtransactionが:
            ある場合：ブロックを作成し、ブロックチェーンに追加する

            ない場合：現在のブロックチェーンの状態と次のブロックに格納するブロックのハッシュ値を永遠と返す
        '''
        self.bb_timer = threading.Timer(CHECK_INTERVAL, self.__generate_block_with_tp)
        self.bb_timer.start()

    def stop_block_building(self):
        print('Thread for __generate_block_with_tp is stopped now')
        self.bb_timer.cancel()

    def start(self):
        '''
        server待受開始のメッセージ送信
        transactionPoolから
        '''
        self.server_state = STATE_STANDBY
        self.cm.start()
        self.start_block_building()
        
    def join_network(self):
        if self.core_node_host != None:
            self.server_state = STATE_CONNECTED_TO_CENTRAL
            self.cm.join_network(self.core_node_host, self.core_node_port)
        else:
            print('This server is runnning as Genesis Core Node...')

    def shutdown(self):
        self.server_state = STATE_SHUTTING_DOWN
        self.flag_stop_block_build = True
        print('Shutdown server...')
        self.cm.connection_close()
        self.stop_block_building()
    
    def get_my_current_state(self):
        return self.server_state

    def send_req_full_chain_to_my_peer(self):
        print('send_req_full_chain_to_my_central called')
        new_message = self.cm.get_message_text(MSG_REQUEST_FULL_CHAIN)
        self.cm.send_msg((self.core_node_host, self.core_node_port),new_message)

    def get_all_chains_for_resolve_conflict(self):
        '''
        指定したメッセージの種別のプロトコルメッセージを作成、返却
        
        更にネットワークに参加しているすべてのCoreにブロードキャストする
        '''
        print('get_all_chains_for_resolve_conflict called')
        new_message = self.cm.get_message_text(MSG_REQUEST_FULL_CHAIN)
        self.cm.send_msg_to_all_peer(new_message)

    def __generate_block_with_tp(self):
        '''
        transactionpoolにtransactionが:
            ある場合、ブロックを作成し、ブロックチェーンに追加する
            
            ない場合、現在のブロックチェーンの状態と次のブロックに格納するブロックのハッシュ値を永遠と返す

        '''

        print('Thread for generate_block_with_tp started!')
        while not self.flag_stop_block_build:#shutdownフラグが立つまで
            self.is_bb_running = True
            prev_hash = copy.copy(self.prev_block_hash)
            result = self.tp.get_stored_transactions()#transactionpoolのtransactionを格納
            if len(result) == 0:#transactionpoolが空の時
                print('Transaction Pool is empty ...')
                break#このwhile文強制終了
            new_tp = self.bm.remove_useless_transaction(result)#未処理のtransactionの救出
            self.tp.renew_my_transactions(new_tp)#transactionpoolを引数new_tpで上書き
            if len(new_tp) == 0:#transactionpoolが空の時
                break#このwhile文強制終了
            # リワードとしてリストの先頭に自分宛のCoinbaseTransactionを追加する
            total_fee = self.tp.get_total_fee_from_tp()
            # TODO: インセンティブの値をここに直書きするのはイケてないのであとで対処する
            total_fee += 30
            my_coinbase_t = CoinbaseTransaction(self.km.my_address(), total_fee)
            transactions_4_block = copy.deepcopy(new_tp)
            transactions_4_block.insert(0, my_coinbase_t.to_dict())#my_coinbase_t.to_dict()をlistの最初に挿入
            new_block = self.bb.generate_new_block(transactions_4_block, prev_hash)#ここでブロック生成
            # タイミングがどうしてもクロスするので念のため保存前に再度確認
            if new_block.to_dict()['previous_block'] == self.prev_block_hash:#作成したブロックのハッシュ値が直前のブロックから作成したものである時
                self.bm.set_new_block(new_block.to_dict())#ブロックをブロックチェーンに追加する
                self.prev_block_hash = self.bm.get_hash(new_block.to_dict())#作成したブロックからハッシュ値を作成する
                msg_new_block = self.cm.get_message_text(MSG_NEW_BLOCK, json.dumps(new_block.to_dict()))#blockの情報を追加してメッセージを作成して格納
                self.cm.send_msg_to_all_peer(msg_new_block)#作成したメッセージをブロードキャストする
                # ブロック生成に成功したらTransaction Poolはクリアする
                index = len(new_tp)
                self.tp.clear_my_transactions(index)#transactionpoollistすべてクリア
                break
            else:
                print('Bad block. It seems someone already win the PoW.')
                break

        print('Current Blockchain is ... ', self.bm.chain)#現在のブロックチェーンの状態
        print('Current prev_block_hash is ... ', self.prev_block_hash)#次のブロックに格納するブロックのハッシュ値
        
        self.save_log()#ブロックチェーンの内容をセーブする
        

        self.flag_stop_block_build = False
        self.is_bb_running = False
        self.bb_timer = threading.Timer(CHECK_INTERVAL, self.__generate_block_with_tp)#CHECK_INTERVALごとにself.__generate_block_with_tpを実行
        self.bb_timer.start()

    def _check_availability_of_transaction(self, transaction):
        """
        Transactionに含まれているTransactionInputの有効性（二重使用）を検証する
        """
        v_result, used_outputs = self.rsa_util.verify_sbc_transaction_sig(transaction)
        if v_result is not True:
            print('signature verification error on new transaction')
            return False

        for used_o in used_outputs:
            print('used_o', used_o)
            bm_v_result = self.bm.has_this_output_in_my_chain(used_o)
            tp_v_result = self.tp.has_this_output_in_my_tp(used_o)
            bm_v_result2 = self.bm.is_valid_output_in_my_chain(used_o)
            if bm_v_result:
                print('This TransactionOutput is already used', used_o)
                return False
            if tp_v_result:
                print('This TransactionOutput is already stored in the TransactionPool', used_o)
                return False
            if bm_v_result2 is not True:
                print('This TransactionOutput is unknown', used_o)
                return False

        return True

    def _check_availability_of_transaction_in_block(self, transaction):
        """
        Transactionの有効性を検証する（Block用）
        tarnsactionの署名が有効でない場合：False
        ブロックチェーン内で不正なtransaction(outputがinputとして)使われている場合：False
　　　　　チェーン内で認知されていないtransactionを使っていないか、使われている場合：False
        """
        #署名の有効性を検証（有効でない場合Falseを返す）
        v_result, used_outputs = self.rsa_util.verify_sbc_transaction_sig(transaction)
        if v_result is not True:
            print('signature verification error on new transaction')
            return False

        print('used_outputs: ', used_outputs)#outputしたアドレスと値のlist

        for used_o in used_outputs:
            print('used_o: ',used_o)
            bm_v_result = self.bm.has_this_output_in_my_chain(used_o)
            bm_v_result2 = self.bm.is_valid_output_in_my_chain(used_o)
            if bm_v_result2 is not True:#チェーン内で不正なtransactionが使われていないか
                print('This TransactionOutput is unknown', used_o)
                return False
            if bm_v_result:#ブロックチェーン内にブロックがすでに使われている
                print('This TransactionOutput is already used', used_o)
                return False

        return True

    def get_total_fee_on_block(self, block):
        """
        ブロックに格納されているbasicなTransaction全ての手数料の合計値を算出する
        """
        print('get_total_fee_on_block is called')
        transactions = block['transactions']
        result = 0
        for t in transactions:
            t = json.loads(t)#json形式のデータをロード
            is_sbc_t, t_type = self.um.is_sbc_transaction(t)
            if t_type == 'basic':
                total_in = sum(i['transaction']['outputs'][i['output_index']]['value'] for i in t['inputs'])
                total_out = sum(o['value'] for o in t['outputs'])
                delta = total_in  - total_out #手数料の計算
                result += delta

        return result#手数料の合計値

    def check_transactions_in_new_block(self, block):
        """
        ブロック内のTranactionに不正がないか確認する
        t_type:basic
        チェーン内で認知されていないtarannsactionを使ってないか
        ブロック内のtarnsactionの署名が有効であるか
        t_type:coinbase
        手数料は有効であるか
        
        有効の場合：ok. this block is acceptable.を返す
        """
        #block内のtransactionの手数料の合計値を算出
        fee_for_block = self.get_total_fee_on_block(block)
        fee_for_block += 30
        print("fee_for_block: ", fee_for_block)

        transactions = block['transactions']

        counter = 0

        for t in transactions:
            t = json.loads(t)
            # basic, coinbase_transaction以外はスルーチェック
            is_sbc_t, t_type = self.um.is_sbc_transaction(t)
            if is_sbc_t:
                if t_type == 'basic':
                    if self._check_availability_of_transaction_in_block(t) is not True:
                        print('Bad Block. Having invalid Transaction')
                        return False
                elif t_type == 'coinbase_transaction':
                    if counter != 0:
                        print('Coinbase Transaction is only for BlockBuilder')
                        return False
                    else:
                        insentive = t['outputs'][0]['value']#outputリストの先頭の送信額
                        print('insentive', insentive)
                        if insentive != fee_for_block:
                            print('Invalid value in fee for CoinbaseTransaction', insentive)
                            return False
            else:
                is_verified = self.rsa_util.verify_general_transaction_sig(t)
                if is_verified is not True:
                    return False

        print('ok. this block is acceptable.')
        return True

    def __core_api(self, request, message):

        if request == 'send_message_to_all_peer':
            new_message = self.cm.get_message_text(MSG_ENHANCED, message)
            self.cm.send_msg_to_all_peer(new_message)
            return 'ok'
        elif request == 'send_message_to_all_edge':
            new_message = self.cm.get_message_text(MSG_ENHANCED, message)
            self.cm.send_msg_to_all_edge(new_message)
            return 'ok'
        elif request == 'api_type':
            return 'server_core_api'
        elif request == 'send_message_to_this_pubkey_address':
            print('send_message_to_this_pubkey_address', message[0])
            msg_type = MSG_ENHANCED
            msg_txt = self.cm.get_message_text(msg_type, message[1])
            check_result, target_host, target_port = self.cm.has_this_edge(message[0])
            print('check_result', check_result)
            if check_result:
                print('sending cipher direct message to... ', target_host, target_port)
                self.cm.send_msg((target_host, target_port), msg_txt)
                return 'ok'
            else:
                return None


    def __handle_message(self, msg, is_core, peer=None):
        '''
        connecttionManagerからServerCoreにメッセージを引き渡すためcallbackする関数
        
        ノードが指定されている時:
            
            msg[2]で受信したメッセージ処理する
        '''
        if peer != None:#peerが空ではない時（追加のcoreノードがある時）
            if msg[2] == MSG_REQUEST_FULL_CHAIN:
                print('Send our latest blockchain for reply to : ', peer)
                mychain = self.bm.get_my_blockchain()#ブロックチェーンlistを返す
                chain_data = pickle.dumps(mychain, 0).decode()#mychainをprotcolversion0で、バイト列への直列化
                #chain_dataを格納したプロトコルメッセージを格納↓
                new_message = self.cm.get_message_text(RSP_FULL_CHAIN, chain_data)
                self.cm.send_msg(peer,new_message)#指定したpeer（ノード）にnew_messageを送信
        else:
            if msg[2] == MSG_NEW_TRANSACTION:#todo:新規transactionを登録する処理を呼び出す
                new_transaction = json.loads(msg[4])#messege:payloadのこと　※ここでEdgeノードから受信している
                print('received new_transaction', new_transaction)
                is_sbc_t, _ = self.um.is_sbc_transaction(new_transaction)#transactionのt_typeの判定
                current_transactions = self.tp.get_stored_transactions()#transactionpoolにtransactionがある時listを返す
                if new_transaction in current_transactions:
                    print('this is already pooled transaction: ', new_transaction)#transactionpoolを返す
                    return

                    if not is_sbc_t:
                        print('this is not SimpleBitcoin transaction: ', new_transaction)
                        is_verified = self.rsa_util.verify_general_transaction_sig(new_transaction)
                        if not is_verified:
                            print('Transaction Verification Error')
                            return
                    else:
                        # テスト用に最初のブロックだけ未知のCoinbaseTransactionを許すための暫定処置
                        if self.bm.get_my_chain_length() != 1:
                            checked = self._check_availability_of_transaction(new_transaction)
                            if not checked:
                                print('Transaction Verification Error')
                                return
                    self.tp.set_new_transaction(new_transaction)

                    if not is_core:
                        m_type = MSG_NEW_TRANSACTION
                        new_message = self.cm.get_message_text(m_type, json.dumps(new_transaction))
                        self.cm.send_msg_to_all_peer(new_message)
                else:
                    if not is_sbc_t:#t_typeがunkouwnの時
                        print('this is not SimpleBitcoin transaction: ', new_transaction)
                        is_verified = self.rsa_util.verify_general_transaction_sig(new_transaction)
                        if not is_verified:
                            return
                    else:
                        # テスト用に最初のブロックだけ未知のCoinbaseTransactionを許すための暫定処置
                        if self.bm.get_my_chain_length() != 1:#繋がっているのがganesisブロックだけではない時
                            checked = self._check_availability_of_transaction(new_transaction)
                            if not checked:
                                print('Transaction Verification Error')
                                return
                    self.tp.set_new_transaction(new_transaction)#new_transactionをtransactionpoolに追加

                    if not is_core:#edgeノードから送信されたデータの場合
                        m_type = MSG_NEW_TRANSACTION
                        new_message = self.cm.get_message_text(MSG_NEW_TRANSACTION, json.dumps(new_transaction))#(msg,payload)
                        self.cm.send_msg_to_all_peer(new_message)#ここで他のノードにtransactionが送信される

            elif msg[2] == MSG_NEW_BLOCK:#todo:新規ブロックを検証する処理を呼び出す #ブロックを作った(nanceの計算を終えた)場合

                if not is_core:
                    print('block received from unknown')
                    return

                new_block = json.loads(msg[4])
                print('new_block: ', new_block)
                if self.bm.is_valid_block(self.prev_block_hash, new_block):#ハッシュ値が等しいかを検証する
                    #new_block内のtransactionが有効であるか↓
                    block_check_result = self.check_transactions_in_new_block(new_block)
                    print('block_check_result : ', block_check_result)
                    if block_check_result is not True:#有効でない場合
                        print('previous block hash is ok. but still not acceptable.')
                        self.get_all_chains_for_resolve_conflict()
                        return
                    # ブロック生成が行われていたら一旦停止してあげる（threadingなのでキレイに止まらない場合あり）
                    if self.is_bb_running:
                        self.flag_stop_block_build = True
                    self.prev_block_hash = self.bm.get_hash(new_block)
                    self.bm.set_new_block(new_block)#
                else:
                    #　ブロックとして不正ではないがVerifyにコケる場合は自分がorphanブロックを生成している
                    #　可能性がある
                    self.get_all_chains_for_resolve_conflict()

            elif msg[2] == RSP_FULL_CHAIN:
                #todo:ブロックチェーン送信要求に応じて返却された
                #ブロックチェーンを検証する処理を呼び出す
                if not is_core:
                    print('blockchain received from unknown')
                    return
                # ブロックチェーン送信要求に応じて返却されたブロックチェーンを検証し、有効なものか検証した上で
                # 自分の持つチェインと比較し優位な方を今後のブロックチェーンとして有効化する
                new_block_chain = pickle.loads(msg[4].encode('utf8'))
                result, pool_4_orphan_blocks = self.bm.resolve_conflicts(new_block_chain)
                print('blockchain received')
                if result is not None:#resultにハッシュ値が入っている時
                    self.prev_block_hash = result#ハッシュ値を更新する
                    if len(pool_4_orphan_blocks) != 0:
                        # orphanブロック群の中にあった未処理扱いになるTransactionをTransactionPoolに戻す↓
                        new_transactions = self.bm.get_transactions_from_orphan_blocks(pool_4_orphan_blocks)
                        for t in new_transactions:
                            self.tp.set_new_transaction(t)#transactionpoolにセット
                else:
                    print('Received blockchain is useless...')#受け取ったブロックチェーンは使いものにならない

            elif msg[2] == MSG_ENHANCED:
                # アプリケーションがP2P Network を単なるトランスポートして使うために独自拡張したメッセージはここで処理する。
                # SimpleBitcoin としてはこの種別は使わない
                print('received enhanced message', msg[4])
                has_same = self.mpm_store.has_this_msg(msg[4])

                if has_same is not True:
                    self.mpm_store.add(msg[4])
                    self.mpmh.handle_message(msg[4], self.__core_api, is_core)
    """
    自作エリア-start
    """
    def save_log(self):
        """
        ブロックチェーンと直前のハッシュ値を５秒ごとに保存する
        """
        self.bb_timer = threading.Timer(5, self.save_data)
        self.bb_timer.start()

    def save_data(self):
        """
        現在のブロックチェーン・ハッシュ値をblockchain.txtに書き込み
        """
        print("save blockchain...")
        mychain = self.bm.get_my_blockchain()
        now_hash = self.prev_block_hash
        if mychain is not None:#複数のブロックがある
            with open(b_path,"wb") as f:
                pickle.dump(mychain, f)
            with open(h_path,"wb") as f:
                pickle.dump(now_hash, f)
        else:#genesisブロックしかない
            pass
    
    """
    自作エリア-end
    """
    def __get_myip(self):
        '''
        ローカルIPアドレスを取得して返す
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0] #ローカルIPアドレスを取得する
