import Crypto
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256

import copy
import binascii
import json

class RSAUtil:

    def __init__(self):
        pass

    def verify_signature(self, message, signature, sender_public_key):
        '''
        デジタル署名を検証する

        引数messageをhash値に変換したものと署名signatureを引数sender_public_keyで復号化し、
        元のデータに一致するか検証
        '''
        print('verify_signature was called')
        hashed_message = SHA256.new(message.encode('utf8'))#まずメッセージをhash値に変換する
        verifier = PKCS1_v1_5.new(sender_public_key)#署名にはRSASSA-PKCS1-v1_5を使用する
        result = verifier.verify(hashed_message, binascii.unhexlify(signature))#16進数文字列signatureをバイト列で表している
        print(result)
        return result

    def encrypt_with_pubkey(self, target, pubkey_text):
        """
        与えられた公開鍵で暗号化する

        target:暗号化される文章
        pubkey_text:公開鍵
        """
        pubkey = RSA.importKey(binascii.unhexlify(pubkey_text))
        encrypto = pubkey.encrypt(target, 0)#暗号化
        return encrypto

    def verify_sbc_transaction_sig(self, transaction):
        """
        simple_bitcoin の引数transactionの署名の正当性を検証する
        
        正当性：
        引数messageをhash値に変換したものと署名signatureを引数sender_public_keyで復号化し、
        元のデータに一致するか検証
        """
        print('verify_sbc_transaction_sig was called')
        sender_pubkey_text, used_outputs = self._get_pubkey_from_sbc_transaction(transaction)
        signature = transaction['signature']#サインの内容
        #transactionの新たな複合オブジェクトを作成し、その後元のオブジェクトの中に見つかったオブジェクトのコピーを挿入します
        c_transaction = copy.deepcopy(transaction)
        del c_transaction['signature']#署名を消している？
        target_txt = json.dumps(c_transaction, sort_keys=True)#jsonデータに書き換える
        sender_pubkey = RSA.importKey(binascii.unhexlify(sender_pubkey_text))#transactionから得た受取人アドレスを公開鍵にする
        result = self.verify_signature(target_txt, signature, sender_pubkey)
        return result, used_outputs

    def _get_pubkey_from_sbc_transaction(self, transaction):
        '''
        引数transactionのinputsの元となったoutputの、
        受取人アドレスと送った値のlistを返す
        '''
        print('_get_pubkey_from_sbc_transaction was called')
        input_t_list = transaction['inputs']#inputsの内容を取り出す
        used_outputs = []
        sender_pubkey = ''
        for i in input_t_list:
            #iunputの元となったtransactionのoutputのリストの何番目に格納されているか調べる
            idx = i['output_index']
            #iunputの元となったtransactionのoutputの値を調べる
            tx = i['transaction']['outputs'][idx]
            used_outputs.append(tx)#outputの値を追加
            sender_pubkey = tx['recipient']#outputの受取人アドレスを追加

        return sender_pubkey, used_outputs

    def verify_general_transaction_sig(self, transaction):
        """
        simple_bitcoin 以外のTransactionも署名の形式を統一することで検証を可能にしておく
        """
        print('verify_general_transaction_sig was called')
        sender_pubkey_text = transaction['sender']
        signature = transaction['signature']
        c_transaction = copy.deepcopy(transaction)
        del c_transaction['signature']
        target_txt = json.dumps(c_transaction, sort_keys=True)
        sender_pubkey = RSA.importKey(binascii.unhexlify(sender_pubkey_text))
        result = self.verify_signature(target_txt, signature, sender_pubkey)
        return result
