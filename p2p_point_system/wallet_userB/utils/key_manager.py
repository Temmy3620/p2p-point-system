import Crypto
import Crypto.Random
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256

import copy
import binascii
import json


class KeyManager:

    def __init__(self, privatekey_text = None, pass_phrase= None):
        print('Initializing KeyManager...')
        if privatekey_text:
            self.import_key_pair(privatekey_text, pass_phrase)
        else:
            random_gen = Crypto.Random.new().read#暗号文的な乱数を出力
            self._private_key = RSA.generate(2048, random_gen)#秘密鍵作成
            self._public_key = self._private_key.publickey()#秘密鍵に基づいて公開鍵作成
            self._signer = PKCS1_v1_5.new(self._private_key)#秘密鍵から署名のオブジェクト※署名にはRSASSA-PKCS1-v1_5を使用する
            if pass_phrase is not None:#pass_phraseに入力があった時
                my_pem = self.export_key_pair(pass_phrase)
                my_pem_hex = binascii.hexlify(my_pem).decode('ascii')#バイナリ文字列をASCIIでデコードしたもの
                # とりあえずファイル名は固定
                path = 'my_server_key_pair.pem'
                f1 = open(path,'a')
                f1.write(my_pem_hex)
                f1.close()


    def my_address(self):
        """
        UI表示用の公開鍵情報
        """
        return binascii.hexlify(self._public_key.exportKey(format='DER')).decode('ascii')


    def compute_digital_signature(self, message):
        '''
        elf._private_keyを使ってメッセージに署名する
        '''
        hashed_message = SHA256.new(message.encode('utf8'))#まずメッセージをhash値に変換する
        signer = PKCS1_v1_5.new(self._private_key)#秘密鍵から署名のオブジェクト※署名にはRSASSA-PKCS1-v1_5を使用する
        return binascii.hexlify(signer.sign(hashed_message)).decode('ascii')


    def verify_my_signature(self, message, signature):
        '''
        デジタル署名を検証する

        引数messageをhash値に変換したものと署名signatureを引数sender_public_keyで復号化し、
        元のデータに一致するか検証
        '''
        print('verify_my_signature was called')
        hashed_message = SHA256.new(message.encode('utf8'))
        verifier = PKCS1_v1_5.new(self._public_key)
        result = verifier.verify(hashed_message, binascii.unhexlify(signature))
        print(result)
        return result

    def encrypt_with_my_pubkey(self, target):
        '''
        引数targetを公開鍵で暗号化
        '''
        encrypto = self._public_key.encrypt(target, 0)
        return encrypto


    def decrypt_with_private_key(self, target):
        '''
        引数targetを秘密鍵で復号化
        '''
        decrypto = self._private_key.decrypt(target)
        print('decrypto', decrypto)
        return decrypto

      
    def export_key_pair(self, pass_phrase):
        """
        鍵ペアをPEMフォーマットで書き出す（バックアップ用途）
        秘密鍵作成
        """
        return self._private_key.exportKey(format='PEM', passphrase=pass_phrase)

   
    def import_key_pair(self, key_data, pass_phrase):
        """
        PEMフォーマットでパスワード保護された鍵ペアをファイルから読み込んで設定する
        """
        self._private_key = RSA.importKey(key_data, pass_phrase)#key_dataによる復号化
        self._public_key = self._private_key.publickey()#公開鍵作成
        self._signer = PKCS1_v1_5.new(self._private_key)#秘密鍵を使って署名のオブジェクト　※署名にはRSASSA-PKCS1-v1_5を使用する
