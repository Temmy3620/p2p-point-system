from time import time

class TransactionInput:
    """
    トトランザクションの中でInputに格納するUTXOを指定する
    
    Args:
        transaction:元となったtransaction{Input:[],Output:[]}
        output_index:元となったtransactionのOutputのリストの何番目に格納されているものを使うか指定
    """
    def __init__(self, transaction, output_index):
        self.transaction = transaction
        self.output_index = output_index

    def to_dict(self):
        d = {
            'transaction': self.transaction,
            'output_index': self.output_index
        }
        return d

class TransactionOutput:
    """
    トランザクションの中で Output （送金相手と送る金額）を管理する
    Args:
        recipient:受取人のアドレス
        value :受取人に送る金額
    TransactionOutput.to_dict():
    辞書型 {'recipient':[値],'value':[値]} を返す
    """
    def __init__(self, recipient_address, value):
        self.recipient = recipient_address
        self.value = value

    def to_dict(self):
        d = {
            'recipient': self.recipient,
            'value': self.value
        }
        return d
    
class Transaction:
    """
    持っていないコインを誰かに簡単に送金できてしまっては全く意味がないので、過去のトランザクションにて
    自分を宛先として送金されたコインの総計を超える送金依頼を作ることができないよう、inputs と outputs
    のペアによって管理する

    Args:
        inputs: TransactionInputクラス
        output: TransactionOutputクラス
        t_type : トランザクションのタイプ。今後の拡張で種別の切り分けに使う
        extra : 拡張用途で利用可能な文字列。例えば送金の際にその理由となった記事のURLを格納したい場合などに使う
    """
    def __init__(self, inputs, outputs, extra=None):
        self.inputs = inputs
        self.outputs = outputs
        self.timestamp = time()#時間
        self.t_type = 'basic'
        self.extra = extra


    def to_dict(self):
        '''
        'inputs': 引数self.inputsが関数TransactionInput.to_dictによって処理され、list化される
            'outputs': 引数self.inputsが関数TransactionOutput.to_dictによって処理され、list化される
            'timestamp': self.timestamp, 
            't_type': self.t_type,
            'extra': self.extra
        '''
        d = {
            'inputs': list(map(TransactionInput.to_dict, self.inputs)),#引数self.inputsが関数TransactionInput.to_dictによって処理され、list化される
            'outputs': list(map(TransactionOutput.to_dict, self.outputs)),#引数self.inputsが関数TransactionOutput.to_dictによって処理され、list化される
            'timestamp': self.timestamp, 
            't_type': self.t_type,
            'extra': self.extra
        }

        return d

    def is_enough_inputs(self, fee):
        '''
        TransactionのInputで格納している値の合計と、Outputに格納されている値と手数料の合計の
        差を求め
        差が正:Ture
        差が負:False
        '''
        total_in = sum(i.transaction['outputs'][i.output_index]['value'] for i in self.inputs)#inputされた値の合計
        total_out = sum(int(o.value) for o in self.outputs) + int(fee)#送った値と引数feeの合計
        delta = total_in  - total_out
        if delta >= 0:
            return True
        else:
            return False

    def compute_change(self, fee):
        '''
        お釣り計算する機能：TransactionのInputで格納している値の合計と、Outputに格納されている値と手数料の合計の
        差を求める
        '''
        total_in = sum(i.transaction['outputs'][i.output_index]['value'] for i in self.inputs)
        total_out = sum(int(o.value) for o in self.outputs) + int(fee)
        delta = total_in  - total_out
        return delta

    
class CoinbaseTransaction(Transaction):
    """
    Coinbaseトランザクションは例外的にInputが存在しない。
    
    recipient:受取人アドレス　value:送信金額
    """
    def __init__(self, recipient_address, value=30):
        self.inputs = []
        self.outputs = [TransactionOutput(recipient_address, value)]
        self.timestamp = time()
        self.t_type = 'coinbase_transaction'

    def to_dict(self):
        '''
        #TransactionOutput(recipient_address, value)を~.to_dict()でlist化させて’outputs’に格納
        '''
        d = {
            'inputs': [],
            'outputs': list(map(TransactionOutput.to_dict, self.outputs)),#~.to_dict()でlist化させて’outputs’に格納
            'timestamp' : self.timestamp,
            't_type': self.t_type
        }

        return d

class EngravedTransaction:
    """
    Twitter風のメッセージをブロックチェーンに刻み込むための拡張Transactionタイプ
    各Transactionには後でSenderの秘密鍵で署名をつける
    """
    def __init__(self, sender, sender_alt_name, message, icon_url=None, reply_to=None, original_reply_to=None):
        self.sender = sender
        self.sender_alt_name = sender_alt_name
        self.icon =  icon_url
        self.message = message
        self.timestamp = time()
        self.reply_to = reply_to
        self.original_reply_to = original_reply_to
        self.content_id = sender + str(self.timestamp)
        self.t_type = 'engraved'

    def to_dict(self):
        d = {
            'sender': self.sender,
            'sender_alt_name': self.sender_alt_name,
            'icon': self.icon,
            'timestamp': self.timestamp, 
            'message' : self.message,
            'reply_to': self.reply_to,
            'original_reply_to': self.original_reply_to,
            'id': self.content_id,
            't_type': self.t_type,
        }

        return d


