# -*- coding: utf-8 -*-
from .block import Block
from .block import GenesisBlock

class BlockBuilder:
    '''
    ・Genesisブロックの作成
    ・新規ブロックの作成
    '''

    def __init__(self):
        print('Initializing BlockBuilder...')
        pass #エラー吐かないようにするためにかくのかな？

    def generate_genesis_block(self):
        '''
        Genesisブロックの作成
        '''
        genesis_block = GenesisBlock()#genesisブロックなのでハッシュ値はセットしない
        return genesis_block

    def generate_new_block(self, transaction, previous_block_hash):
        '''
        新規ブロックの作成

        Args:
            transaction: ブロック内にセットされるトランザクション
            previous_block_hash: 直前のブロックのハッシュ値
        '''
        new_block = Block(transaction, previous_block_hash)
        return new_block


