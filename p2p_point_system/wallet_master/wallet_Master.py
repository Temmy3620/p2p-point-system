from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from tkinter.ttk import Button, Style
from tkinter import ttk
import binascii
import os
import json
import sys
import base64
import datetime
import pprint
import copy

from core.client_core import ClientCore as Core
from transaction.transactions import Transaction
from transaction.transactions import CoinbaseTransaction
from transaction.transactions import TransactionInput
from transaction.transactions import TransactionOutput
from transaction.utxo_manager import UTXOManager as UTXM
from utils.key_manager import KeyManager
from utils.rsa_util import RSAUtil
from p2p.message_manager import (

    MSG_NEW_TRANSACTION,
    MSG_ENHANCED,
)


class SimpleBC_Gui(Frame):
    '''
    Args:
       parrent:Tk()
       my_port:自分のノードのポート番号
       c_host:接続するネットワークのIPアドレス
       c_port:接続するエリアのポート番号
    '''
  
    def __init__(self, parent, my_port, c_host, c_port):
        Frame.__init__(self, parent)
        self.parent = parent
        self.parent.protocol('WM_DELETE_WINDOW', self.quit)
        self.coin_balance = StringVar(self.parent, '0')#残高　StringVerを使うことによって残高が変更で、表示も更新できる
        self.status_message = StringVar(self.parent, 'Ready')
        self.c_core = None
        self.initApp(my_port, c_host, c_port)#ソケット開く、coreノード接続
        self.setupGUI()

    def quit(self, event=None):
        """
        アプリの終了
        """
        self.c_core.shutdown()
        self.parent.destroy()


    def initApp(self, my_port, c_host, c_port):
        """
        ClientCoreとの接続含めて必要な初期化処理はここで実行する
        """
        print('SimpleBitcoin client is now activating ...: ')

        self.km = KeyManager() 
        self.um = UTXM(self.km.my_address())#my_addressに自分のadressを入れる
        self.rsa_util = RSAUtil()

        self.c_core = Core(my_port, c_host, c_port, self.update_callback)#client_serverインスタンスの作成
        self.c_core.start()

        # テスト用途（本来はこんな処理しない）
        t1 = CoinbaseTransaction(self.km.my_address())
        t2 = CoinbaseTransaction(self.km.my_address())
        t3 = CoinbaseTransaction(self.km.my_address())

        transactions = []
        transactions.append(t1.to_dict())
        transactions.append(t2.to_dict())
        transactions.append(t3.to_dict())
        self.um.extract_utxos(transactions)

        self.update_balance()
      

    def display_info(self, title, info):
        """
        ダイアログボックスを使ったメッセージの表示
        """
        f = Tk()
        label = Label(f, text=title)
        label.pack()#配置
        info_area = Text(f, width=70, height=50)
        info_area.insert(INSERT, info)#内容(info)をText内に表示
        info_area.pack()
          

    def update_callback(self):
        print('update_callback was called!')
        s_transactions = self.c_core.get_stored_transactions_from_bc()
        print(s_transactions)
        self.um.extract_utxos(s_transactions)
        self.update_balance()


    def update_status(self, info):
        """
        画面下部のステータス表示内容を変更する
        """  
        self.status_message.set(info)


    def update_balance(self):
        """
        総額表示の内容を最新状態に合わせて変更する
        """
        bal = str(self.um.my_balance)#所持金の総額を文字に変える
        self.coin_balance.set(bal)#


    def create_menu(self):
        """
        メニューバーに表示するメニューを定義する
        """
        top = self.winfo_toplevel()
        self.menuBar = Menu(top)
        top['menu'] = self.menuBar

        #タブ1menu
        self.subMenu = Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label='Settings', menu=self.subMenu)
        
        self.subMenu.add_command(label='Show My Address', command=self.show_my_address)
        #self.subMenu.add_command(label='Load my Keys', command=self.show_input_dialog_for_key_loading)
        #self.subMenu.add_command(label='Update Blockchain', command=self.update_block_chain)#ブロックチェーンの内容をwalletに反映させる
        self.subMenu.add_separator()
        self.subMenu.add_command(label='Quit', command=self.quit)
        
        #タブ2Settings
        self.subMenu2 = Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label='Blockchain', menu=self.subMenu2)
        #self.subMenu2.add_command(label='Renew my Keys', command=self.renew_my_keypairs)#全く新しい鍵のペアを更新する(セキュリティのため？)
        self.subMenu2.add_command(label='Update Blockchain', command=self.update_block_chain)#ブロックチェーンの内容をwalletに反映させる
        self.subMenu2.add_command(label='Show Blockchain', command=self.show_my_block_chain)#現在のブロックチェーンの状態を見る

        #タブ3Advance
        self.subMenu3 = Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label='Message', menu=self.subMenu3)
        #self.subMenu3.add_command(label='Show Blockchain', command=self.show_my_block_chain)#現在のブロックチェーンの状態を見る


    
    def show_my_address(self):
        '''
        自分のアドレスを表示する
        '''
        f = Tk()
        label = Label(f, text='My Address')
        label.pack()#labelの配置
        key_info = Text(f, width=70, height=10)
        my_address = self.km.my_address()#公開鍵情報を取得
        key_info.insert(INSERT, my_address)#textに代入している
        key_info.pack()#配置


    def show_input_dialog_for_key_loading(self):
    
        def load_my_keys():
            # ファイル選択ダイアログの表示
            f2 = Tk()
            f2.withdraw()
            fTyp = [('','*.pem')]
            iDir = os.path.abspath(os.path.dirname(__file__))
            messagebox.showinfo('Load key pair','please choose your key file')
            #フォルダを選択するダイアログを開く↓
            f_name = filedialog.askopenfilename(filetypes = fTyp,initialdir = iDir)
            
            try:
                file = open(f_name)
                data = file.read()
                target = binascii.unhexlify(data)
                # TODO: 本来は鍵ペアのファイルが不正などの異常系処理を考えるべき
                self.km.import_key_pair(target, p_phrase.get())
            except Exception as e:
                print(e)
            finally:
                # TODO: 所有コインの再確認処理を入れる必要あり
                file.close()
                f.destroy()
                f2.destroy()
                self.um = UTXM(self.km.my_address())
                self.um.my_balance = 0
                self.update_balance()
    
        f = Tk()
        label0 = Label(f, text='Please enter pass phrase for your key pair')
        frame1 = ttk.Frame(f)
        label1 = ttk.Label(frame1, text='Pass Phrase:')

        p_phrase = StringVar()

        entry1 = ttk.Entry(frame1, textvariable=p_phrase) 
        button1 = ttk.Button(frame1, text='Load', command=load_my_keys)

        label0.grid(row=0,column=0,sticky=(N,E,S,W))
        frame1.grid(row=1,column=0,sticky=(N,E,S,W))
        label1.grid(row=2,column=0,sticky=E)
        entry1.grid(row=2,column=1,sticky=W)
        button1.grid(row=3,column=1,sticky=W)


    def update_block_chain(self):
        self.c_core.send_req_full_chain_to_my_core_node()

    def renew_my_keypairs(self):
        """
        利用する鍵ペアを新しいものに更新する。
        """
        def save_my_pem():
            self.km = KeyManager()
            my_pem = self.km.export_key_pair(p_phrase)
            my_pem_hex = binascii.hexlify(my_pem).decode('ascii')
            # とりあえずファイル名は固定
            path = 'my_key_pair.pem'
            f1 = open(path,'a')
            f1.write(my_pem_hex)
            f1.close()

            f.destroy()
            self.um = UTXM(self.km.my_address())
            self.um.my_balance = 0
            self.update_balance()
            
        f = Tk()
        f.title('New Key Gene')
        label0 = Label(f, text='Please enter pass phrase for your new key pair')
        frame1 = ttk.Frame(f)
        label1 = ttk.Label(frame1, text='Pass Phrase:')

        p_phrase = StringVar()

        entry1 = ttk.Entry(frame1, textvariable=p_phrase) 
        button1 = ttk.Button(frame1, text='Generate', command=save_my_pem)

        label0.grid(row=0,column=0,sticky=(N,E,S,W))
        frame1.grid(row=1,column=0,sticky=(N,E,S,W))
        label1.grid(row=2,column=0,sticky=E)
        entry1.grid(row=2,column=1,sticky=W)
        button1.grid(row=3,column=1,sticky=W)


    def show_my_block_chain(self):
        """
        自分が保持しているブロックチェーンの中身を確認する
        """
        mychain = self.c_core.get_my_blockchain()
        if mychain is not None:#複数(2)のブロックがある
            mychain_str = pprint.pformat(mychain, indent=2)
            self.display_info('Current Blockchain', mychain_str)
        else:#genesisブロックしかない
            self.display_info('Warning', 'Currently Blockchain is empty...')


  
    def setupGUI(self):
        """
        画面に必要なパーツを並べる
        """

        self.parent.bind('<Control-q>', self.quit)#イベント：「Contrl+q」でアプリの終了
        self.parent.title('MasterUser GUI')#タイトル
        self.pack(fill=BOTH, expand=1)#縦横拡大、レスポンシブあり

        self.create_menu()#タブを設ける

        lf = LabelFrame(self, text='Current Balance')#ラベル
        lf.pack(side=TOP, fill='both', expand='yes', padx=7, pady=7)

        lf2 = LabelFrame(self, text='')#ラベル
        lf2.pack(side=BOTTOM, fill='both', expand='yes', padx=7, pady=7)
    
        #所持コインの総額表示領域のラベル
        self.balance = Label(lf, textvariable=self.coin_balance, font='Helvetica 20')
        self.balance.pack()

        #受信者となる相手の公開鍵
        self.label = Label(lf2, text='Recipient Address:')
        self.label.grid(row=0, pady=5)
        #ここ↓に入力する(Entry)
        self.recipient_pubkey = Entry(lf2, bd=2)
        self.recipient_pubkey.grid(row=0, column=1, pady=5)

        # 送金額
        self.label2 = Label(lf2, text='Amount to pay :')
        self.label2.grid(row=1, pady=5)
        #ここ↓に入力する(Entry)
        self.amountBox = Entry(lf2, bd=2)
        self.amountBox.grid(row=1, column=1, pady=5, sticky='NSEW')

        # 手数料
        self.label3 = Label(lf2, text='Fee (Optional) :')
        self.label3.grid(row=2, pady=5)
        #ここ↓に入力する(Entry)
        self.feeBox = Entry(lf2, bd=2)
        self.feeBox.grid(row=2, column=1, pady=5, sticky='NSEW')

        # 間隔の開け方がよくわからんので空文字で場所確保
        self.label4 = Label(lf2, text='')
        self.label4.grid(row=5, pady=5)

        # 送金実行ボタン
        self.sendBtn = Button(lf2, text='\nSend point(s)\n', command=self.sendCoins)
        self.sendBtn.grid(row=6, column=1, sticky='NSEW')

        # 下部に表示するステータスバー
        stbar = Label(self.winfo_toplevel(), textvariable=self.status_message, bd=1, relief=SUNKEN, anchor=W)
        stbar.pack(side=BOTTOM, fill=X)

  
    # 送金実行ボタン押下時の処理実体
    def sendCoins(self):
        sendAtp = self.amountBox.get()#送ったコインの値を取得
        recipientKey = self.recipient_pubkey.get()#受信者アドレス取得
        sendFee = self.feeBox.get()#手数料取得

        utxo_len = len(self.um.utxo_txs)#UTXOtransactionのデータを取得する

        if not sendAtp:#何も入力しなかった場合
            messagebox.showwarning('Warning', 'Please enter the Amount to pay.')#ダイアログが現れる
            return
        elif len(recipientKey) <= 1:#アドレス欄が１文字以下の場合
            messagebox.showwarning('Warning', 'Please enter the Recipient Address.')#ダイアログが現れる
            return
        else:
            #もう一度入力を確認させる(yesかnoで)
            result = messagebox.askyesno('Confirmation', 'Sending {} SimpleBitcoins to :\n {}'.format(sendAtp, recipientKey))

        if not sendFee:#手数料欄に入力がない場合
            sendFee = 0#手数料は０とする


        if result:#送信をyesにした時
            if 0 < utxo_len:
                #サーバーに、このアドレスにsendAtpだけ送ったことが表示される
                print('Sending {} SimpleBitcoins to reciever:\n {}'.format(sendAtp, recipientKey))
            else:
                messagebox.showwarning('Short of Coin.', 'Not enough coin to be sent...')
                return

            utxo, idx = self.um.get_utxo_tx(0)#最初はcoinbaseのtransactionが入っている

            t = Transaction(
                [TransactionInput(utxo, idx)],
                [TransactionOutput(recipientKey, int(sendAtp))]
            )

            counter = 1
            # TransactionInputが送信額を超えるまで繰り返して取得しTransactionとして完成させる
            if type(sendFee) is not str:
                sendFee = int(sendFee)
            while t.is_enough_inputs(sendFee) is not True:#transactionの内容が正しくない場合
                new_utxo, new_idx = self.um.get_utxo_tx(counter)
                t.inputs.append(TransactionInput(new_utxo, new_idx))
                counter += 1
                if counter > utxo_len:
                    messagebox.showwarning('Short of Coin.', 'Not enough coin to be sent...')
                    break

            # 正常なTransactionが生成できた時だけ秘密鍵で署名を実行する
            if t.is_enough_inputs(sendFee) is True:#trasactionの内容が正しい時
                # まずお釣り用Transactionを作る
                change = t.compute_change(sendFee)#所持金を求める
                t.outputs.append(TransactionOutput(self.km.my_address(), change))
                to_be_signed = json.dumps(t.to_dict(), sort_keys=True)
                signed = self.km.compute_digital_signature(to_be_signed)#transactionのデータを秘密鍵で署名する
                new_tx = json.loads(to_be_signed)#jsonデータにする
                new_tx['signature'] = signed#署名したものをsignatureとして格納
                # TransactionをP2P Networkに送信
                tx_strings = json.dumps(new_tx)#json形式に整形して出力
                self.c_core.send_message_to_my_core_node(MSG_NEW_TRANSACTION, tx_strings)#ここでtransactionをCoreノードに送信
                print('signed new_tx:', tx_strings)
                # 実験的にお釣り分の勘定のため新しく生成したTransactionをUTXOとして追加しておくが
                # 本来はブロックチェーンの更新に合わせて再計算した方が適切
                self.um.put_utxo_tx(t.to_dict())
                to_be_deleted = 0
                del_list = []
                while to_be_deleted < counter:
                    del_tx = self.um.get_utxo_tx(to_be_deleted)
                    del_list.append(del_tx)
                    to_be_deleted += 1

                for dx in del_list:
                    self.um.remove_utxo_tx(dx)
        #それぞれ入力した値を消す
        self.amountBox.delete(0,END)
        self.feeBox.delete(0,END)
        self.recipient_pubkey.delete(0,END)
        self.update_balance()

 
def main(my_port, c_host, c_port):
  
    root = Tk()
    app = SimpleBC_Gui(root, my_port, c_host, c_port)
    root.mainloop()


if __name__ == '__main__':

    args = sys.argv
 
    if len(args) == 4:
        my_port = int(args[1])#~$python スクリプト args[1] args[2] args[3]
        c_host = args[2]
        c_port = int(args[3])
    else:
        print('Param Error')
        print('$ Wallet_App.py <my_port> <core_node_ip_address> <core_node_port_num>')
        quit()

    main(my_port, c_host, c_port)
