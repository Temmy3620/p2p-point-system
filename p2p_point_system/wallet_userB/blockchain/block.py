import json
from time import time
import hashlib
import binascii
from datetime import datetime

class Block:
    def __init__(self, transactions, previous_block_hash):
        """
        Args:
            transaction: ブロック内にセットされるトランザクション
            previous_block_hash: 直前のブロックのハッシュ値
        """
        snap_tr = json.dumps(transactions)  # PoW計算中に値が変わるのでブロック計算開始時の値を退避させておく

        self.timestamp = time()#時間
        self.transactions = json.loads(snap_tr)
        self.previous_block = previous_block_hash

        current = datetime.now().strftime("%Y/%m/%d %H:%M:%S")#現在時刻
        print('start_create_genesisblock:' + current)

        json_block = json.dumps(self.to_dict(include_nonce=False) , sort_keys=True)
        print('json_block :', json_block)
        self.nonce = self.get_nonce_for_pow(json_block)

        current2 = datetime.now().strftime("%Y/%m/%d %H:%M:%S")#現在時刻
        print("nance_was_computed:"+ current2)#nanceの計算が終わった後の時刻
    
    def to_dict(self, include_nonce= True):
        d = {
            'timestamp' : self.timestamp,
            'transactions' : list(map(json.dumps, self.transactions)),
            'previous_block': self.previous_block
        }

        if include_nonce:#ナンス追加処理
            d['nonce'] = self.nonce
        return d

    def get_nonce_for_pow(self, message, difficulty=3):
        '''
        引数からnanceの計算を行う
        digestが~000になるまでnonceを増やす　なったらnonceを返す
        '''
        # difficultyの数字を増やせば増やすほど、末尾で揃えなければならない桁数が増える。
        # macbookくらいの端末で基準値は5
        i = 0
        suffix = '0' * difficulty #'000'
        while True:
            nonce = str(i)#総当り的に数字を増やして試す 最初は0次は1
            digest = binascii.hexlify(self._get_double_sha256((message + nonce).encode('utf-8'))).decode('ascii')#UTF-8でエンコードされたものをASCIIでデコードする
            if digest.endswith(suffix):#digestの末尾が~000になるまでnonceを増やす
                return nonce
            i += 1

    def _get_double_sha256(self, message):
        '''
        SHA256でバイト文字列を取得する

        return バイト文字列（バイト文字列(メッセージ)）
        '''
        return hashlib.sha256(hashlib.sha256(message).digest()).digest()

        
class GenesisBlock(Block):
    """
    前方にブロックを持たないブロックチェーンの始原となるブロック。
    transaction にセットしているのは「{"message":"this_is_simple_bitcoin_genesis_block"}」をSHA256でハッシュしたもの。深い意味はない
    """
    def __init__(self):
        super().__init__(transactions='AD9B477B42B22CDF18B1335603D07378ACE83561D8398FBFC8DE94196C65D806', previous_block_hash=None)

    def to_dict(self, include_nonce=True):
        d = {
            'transactions': self.transactions,
            'genesis_block': True,
        }
        if include_nonce:
            d['nonce'] = self.nonce
        return d