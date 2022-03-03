class UTXOManager:

    def __init__(self, address):
        print('Initializing UTXOManager...')
        self.my_address = address
        self.utxo_txs = []
        self.my_balance = 0


    def get_txs_to_my_address(self, txs):
        """
        与えられたTransaction群の中から自分宛のもののみを抽出して返却する

        outputに自分宛て(my_address)のアドレスがあるtransactionを格納してlistで返す
        """
        my_txs = []
        for t in txs:

            result, t_type = self.is_sbc_transaction(t)#t_typeの判定

            if result is not True:#t_typeのunknown
                print('This is not for simple_bitcoin transaction')
                continue

            for txout in t['outputs']:
                recipient = txout['recipient']

                if recipient == self.my_address:
                    my_txs.append(t)#outputに自分宛て(my_address)のアドレスがあるtransactionを格納する

        return my_txs


    def get_txs_from_my_address(self, txs):
        """
        与えられたTransaction群(引数txs)の中から自分が送信したもののみを抽出して返却する
        """
        my_txs = []  
        for t in txs:
            has_my_output = False
            result, t_type = self.is_sbc_transaction(t)#t_typeの判定
            if result is not True:#t_typeがcoinbaseまたbasicではない時
                print('This is not for simple_bitcoin transaction')
                continue
            for txin in t['inputs']:
                t_in_txin = txin['transaction']#inputの元となったtransaction
                idx = txin['output_index']#inputの元なったtransactionのOutputlistの自分が格納されている番号の
                o_recipient = t_in_txin['outputs'][idx]['recipient']#続き⇒受取人アドレス
                if o_recipient == self.my_address:#inputに自分のアドレス(my_address)がある場合
                    has_my_output = True
                    
            if has_my_output:
                my_txs.append(t)#inputに自分宛のアドレス(my_address)があるtransaction追加

        print('transactions from me:', my_txs)
        return my_txs #自分が送信したtransaction

    def extract_utxos(self, txs):
        """
        与えられたTransaction群の中からUTXOとしてまだ利用可能なもののみを抽出して保存する
        """
        print('extract_utxos called!')

        outputs = []#outputに自分のアドレスがあるtransactionを格納
        inputs = []#inputに自分のアドレスがあるtransactionを格納
        idx = 0    
        for t in txs:
            result, _ = self.is_sbc_transaction(t)#t_typeの判定
            if result is not True:#t_typeがunkwonの時
                print('This is not for simple_bitcoin transaction')
                continue
            for txout in t['outputs']:
                recipient = txout['recipient']
                if recipient == self.my_address:
                    outputs.append(t)#outputに自分のアドレスがあるtransactionを格納
            for txin in t['inputs']:
                t_in_txin = txin['transaction']
                idx = txin['output_index']
                o_recipient = t_in_txin['outputs'][idx]['recipient']
                if o_recipient == self.my_address:
                    inputs.append(t)#inputに自分のアドレスがあるtransactionを格納
        
        if outputs is not []:#outputsが空ではない時
            for o in outputs:
                if inputs is not []:#inputsが空ではない時
                    for i in inputs:
                        for i_i in i['inputs']:
                            if o == i_i['transaction']:
                                
                                outputs.remove(o)#すでに使われたものを削除する
                else:
                    break
        else:
            print('No Transaction for UTXO')
            return
                    
        self._set_my_utxo_txs(outputs)


    def _set_my_utxo_txs(self, txs):
        """
        一括でUTXOトランザクション群を書き換える
        自分宛のoutputが格納されているtransactionをタプルで格納
        """
        print('_set_my_utxo_txs was called')
        self.utxo_txs = []#一度listをクリアする

        for t in txs:
            self.put_utxo_tx(t)#outputに自分宛てのアドレスがあるtransactionをタプルでutxo_txs[]に格納


    def is_sbc_transaction(self, tx):
        """
        暗号通貨用のTransactionかそれ以外かを判定する。
        便利なので種別も一緒に返す
        
        引数txからreturn coinbase or basicの時:Ture   unkownの時:False
        """
        print(tx['t_type'])
        tx_t = tx['t_type']#transactionからtypeを抜き出す

        t_basic = 'basic'
        t_coinbase = 'coinbase_transaction'
        unknown = 'unknown'

        if tx_t != t_basic:
            if tx_t != t_coinbase:#タイプがbasicでもcoinbaseでもない時
                return False, unknown
            else:
                return True, t_coinbase#タイプがcoinbaseの時
        else:
            return True, t_basic#タイプがbasicの時


    def put_utxo_tx(self, tx):
        """
        utxoトランザクションの追加。Transactionと自身宛のoutputが格納されている
        インデックスのタプルとして保存する
        (transaction, 数字)：outputに自分宛てのアドレスがある時
        """
        print('put_utxo_tx was called')
        idx = 0
        for txout in tx['outputs']:
            if txout['recipient'] == self.my_address:
                self.utxo_txs.append((tx, idx))#タプルをlistに追加
            else:
                idx += 1

        self._compute_my_balance()


    def get_utxo_tx(self, idx):
        """
        idxで指定されたUTXOを返す

        return self.utxo_txs[idx]
        """
        return self.utxo_txs[idx]


    def remove_utxo_tx(self, tx):
        """
        使用済みトランザクションの削除
        引数txで指定した要素をリストから削除する
        """
        self.utxo_txs.remove(tx) #txで指定した要素を削除する
        self._compute_my_balance()


    def _compute_my_balance(self):
        """
        outputの利用可能額の合計値を計算する
        """
        print('_compute_my_balance was called')
        balance = 0
        txs = self.utxo_txs
        for t in txs:#UTXOを一個一個取り出す
            for txout in t[0]['outputs']:
                print('txout:', txout)
                if txout['recipient'] == self.my_address:
                    balance += txout['value']#outputsの値を足す

        self.my_balance = balance
