import json
import hashlib
import binascii
import pickle
import copy
import threading


class BlockchainManager:

    def __init__(self, genesis_block):
        print('Initializing BlockchainManager...')
        self.chain = []
        self.lock = threading.Lock()
        self.__set_my_genesis_block(genesis_block)

    def __set_my_genesis_block(self, block):
        '''
        Genesisブロックをブロックチェーンに追加する
        '''
        self.genesis_block = block
        self.chain.append(block)#ブロックチェーンにGenesisブロックを追加

    def set_new_block(self, block):
        '''
        新規ブロックをブロックチェーンに追加する
        '''
        with self.lock:
            self.chain.append(block)#ブロックチェーンにブロックを追加

    def renew_my_blockchain(self, blockchain):
        '''
        # ブロックチェーン自体を更新し、それによって変更されるはずの最新のprev_block_hashを計算して返却する
        '''
        with self.lock:
            if self.is_valid_chain(blockchain):
                self.chain = blockchain
                latest_block = self.chain[-1]#最後のブロックを取得する
                return self.get_hash(latest_block)#最後のブロックからハッシュ値を取る
            else:
                print('invalid chain cannot be set...')
                return None

    def get_my_blockchain(self):
        '''
        ブロックチェーンにGenesisブロック以外のブロックも繋がっているときブロックチェーンを返す
        '''
        if len(self.chain) > 1:
            return self.chain
        else:
            return None
            
    def get_my_chain_length(self):
        '''
        ブロックチェーンのブロック数を返す
        '''
        return len(self.chain)


    def get_stored_transactions_from_bc(self):
        '''
        ブロックチェーン内の各ブロックのtransactionを一個一個追加した
        全transactionのlistを返す
        '''
        print('get_stored_transactions_from_bc was called!')
        current_index = 1
        stored_transactions = []

        while current_index < len(self.chain):#すべてのtransactionを参照する
            block = self.chain[current_index]#参照されてないブロックを取り出す
            transactions = block['transactions']#トランザクションを取り出す

            for t in transactions:#transactionを一個一個取り出す
                stored_transactions.append(json.loads(t))#取り出したtransactionを追加する

            current_index += 1

        return stored_transactions


    def get_transactions_from_orphan_blocks(self, orphan_blocks):
        '''
        引数orphan_blocksから一つ一つブロックを取り出しtransactionを参照し、

        与えられたTransactionのリストの中で既に自分が管理するブロックチェーン内に含まれたTransactionがある場合、
        
        それを削除したものを返却する
        '''
        current_index = 1
        new_transactions = []

        while current_index < len(orphan_blocks):#
            block = orphan_blocks[current_index]
            transactions = block['transactions']
            target = self.remove_useless_transaction(transactions)
            for t in target:
                new_transactions.append(t)

        return new_transactions


    def remove_useless_transaction(self, transaction_pool):
        """
        与えられたTransactionのリストの中で既に自分が管理するブロックチェーン内に含まれたTransactionがある場合、それを削除したものを返却する
            param :
                transaction_pool: 検証したいTransactionのリスト。TransactionPoolに格納されているデータを想定

            return :
                整理されたTransactionのリスト。与えられたリストがNoneの場合にはNoneを返す
        """

        if len(transaction_pool) != 0:
            current_index = 1

            while current_index < len(self.chain):
                block = self.chain[current_index]
                transactions = block['transactions']
                for t in transactions:
                    for t2 in transaction_pool:
                        # ブロックに格納するタイミングで json.dumps してるので普通に比較すると死ぬ
                        if t == json.dumps(t2):
                            print('already exist in my blockchain :', t2)
                            transaction_pool.remove(t2)

                current_index += 1
            return transaction_pool
        else:
            print('no transaction to be removed...')
            return []

    def resolve_conflicts(self, chain):
        '''
        自分のブロックチェーンと比較して、長い方を有効とする。
        
        return result:最新ハッシュ値　pool_4_orphan_block:有効なブロックチェーン
        '''
        # 自分のブロックチェーンと比較して、長い方を有効とする。有効性検証自体はrenew_my_blockchainで実施
        mychain_len = len(self.chain)
        new_chain_len = len(chain)

        pool_4_orphan_blocks = copy.deepcopy(self.chain)
        has_orphan = False

        # 自分のチェーンの中でだけ処理済みとなっているTransactionを救出する。現在のチェーンに含まれていない
        # ブロックを全て取り出す。時系列を考えての有効無効判定などはしないかなり簡易な処理。
        if new_chain_len > mychain_len:
            for b in pool_4_orphan_blocks:
                for b2 in chain:
                    if b == b2:
                        pool_4_orphan_blocks.remove(b)

            result = self.renew_my_blockchain(chain)
            print(result)
            if result is not None:
                return result, pool_4_orphan_blocks
            else:
                return None, []
        else:
            print('invalid chain cannot be set...')
            return None, []

    def is_valid_block(self, prev_block_hash, block, difficulty=3):
        '''
        ブロック単体の正当性を検証する
        
        正当性:引数のblockのhash値と引数のhash値が異なる時、Falseを返す
        引数のblockのhash値と引数のhash値が等しく、かつ
        ブロックの正当性検証につかうdigestの末尾が'000'で終わる場合 Tureを返す
        '''
        # ブロック単体の正当性を検証する
        suffix = '0' * difficulty # >>>'000'
        block_4_pow = copy.deepcopy(block)#blockの深いコピーを格納する
        #※深いコピー：新たな複合オブジェクトを作成し、その後元のオブジェクト中に見つかったオブジェクトのコピーを格納
        nonce = block_4_pow['nonce']
        del block_4_pow['nonce']#nonce項目の削除
        print(block_4_pow)

        message = json.dumps(block_4_pow, sort_keys=True)
        # print("message", message)
        nonce = str(nonce)#nonceを文字列に変換して格納

        if block['previous_block'] != prev_block_hash:#直前のブロックのhash値が引数のブロックのhash値と異なる時
            print('Invalid block (bad previous_block)')
            print(block['previous_block'])
            print(prev_block_hash)
            return False
        else:
            #正当性検証に使うハッシュ値を作っている↓
            digest = binascii.hexlify(self._get_double_sha256((message + nonce).encode('utf-8'))).decode('ascii')
            if digest.endswith(suffix):#digestが文字列suffixで終わるかチェック
                print('OK, this seems valid block')
                return True
            else:#含まれない
                print('Invalid block (bad nonce)')
                print('nonce :' , nonce)
                print('digest :' , digest)
                print('suffix', suffix)
                return False

    def is_valid_chain(self, chain):
        '''
        ブロック全体の正当性を検証する
        直前のブロックから得られているhash値と次の
        '''
        # ブロック全体の正当性を検証する
        last_block = chain[0]#Genesisブロック
        current_index = 1

        while current_index < len(chain):#チェーン内のブロックをすべて参照
            block = chain[current_index]#参照されていないブロックをすべて追加
            if self.is_valid_block(self.get_hash(last_block), block) is not True:#直前のブロックから得られるhash値と参照されているブロックのhash値が異なる場合Falseを返す
                last_block = chain[current_index]
            current_index += 1

        return True


    def has_this_output_in_my_chain(self, transaction_output):
        """返す
        保存されているブロックチェーン内ですでにこのTransactionOutputがInputとして使われていないか？の確認

        返り値はTrueがすでに存在しているということだから、Transactionの有効性としてNGを意味していることに注意
        """
        print('has_this_output_in_my_chain was called!')
        current_index = 1
        
        if len(self.chain) == 1:
            print('only the genesis block is in my chain')
            return False

        while current_index < len(self.chain):#ブロックをすべて参照する
            block = self.chain[current_index]#参照されてないGanasisブロック以外のブロックを取り出す
            transactions = block['transactions']#transactionを取り出す

            for t in transactions:#transactionを順番に取り出す
                t = json.loads(t)#jsonファイルとして保存されているデータを取り出す
                if t['t_type'] == 'basic' or t['t_type'] == 'coinbase_transaction':#transactionのタイプがbasicまたはコインベースの時
                    if t['inputs'] != []:#キー'inputs'がからではない時
                        inputs_t = t['inputs']#キー'inputs'の値を取り出す
                        for it in inputs_t:
                            print(it['transaction']['outputs'][it['output_index']])
                            if it['transaction']['outputs'][it['output_index']] == transaction_output:
                                print('This TransactionOutput was already used', transaction_output)
                                return True

            current_index += 1

        return False


    def is_valid_output_in_my_chain(self, transaction_output):
        """
        チェーン内で認知されていない不正なTransactionを使ってないか確認
        テスト用に気軽にCoinbaseTransaction使えなくなるので有効化させる時は注意
        """
        
        print('is_valid_output_in_my_chain was called!')
        current_index = 1

        while current_index < len(self.chain):
            block = self.chain[current_index]#参照されてないGanasisブロック以外のブロックを取り出す
            transactions = block['transactions']#transactionを取り出す

            for t in transactions:#transactionを順番に取り出す
                t = json.loads(t)#jsonファイルとして保存されているデータを読み込む
                #
                if t['t_type'] == 'basic' or t['t_type'] == 'coinbase_transaction':
                    outputs_t = t['outputs']#toransactionの出力値を取り出す
                    #取り出したtransaction出力値が引数と一致した場合Trueを返す
                    for ot in outputs_t:
                        if ot == transaction_output:
                            return True

            current_index += 1

        return False
                         

    def _get_double_sha256(self,message):
        '''
        SHA256でバイト文字列を取得する

        return バイト文字列（バイト文字列(メッセージ)）
        '''
        return hashlib.sha256(hashlib.sha256(message).digest()).digest()#バイト文字列のダイジェストを返す

    def get_hash(self,block):
        """
        正当性確認に使うためブロックのハッシュ値を取る
            param 
                block: Block
        """
        print('BlockchainManager: get_hash was called!')
        block_string = json.dumps(block, sort_keys=True)#辞書型を文字列に変換してソートする
        # print("BlockchainManager: block_string", block_string)
        return binascii.hexlify(self._get_double_sha256((block_string).encode('utf-8'))).decode('ascii')#UTF-8でエンコードされたものをASCIIでデコードする
