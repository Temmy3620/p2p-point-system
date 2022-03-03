### Tested System:
* OSX 10.12.6
* python 3.8.10

```bash:
Copyright 2022 KIT Ninagawa lab
Released under the MIT license.
see https://opensource.org/licenses/MIT
```

### サーバー１の起動

```bash:
python primordial_server.py 50082 xxx.xxx.xxx.xxx
```

### サーバー２の起動

```bash:
python system_server.py 50085 xxx.xxx.xxx.xxx 50082 test
```

### サーバー3の起動

```bash:
python system_server.py 50088 xxx.xxx.xxx.xxx 50085 test
```

### クライアント（Edgeノード）の起動

```bash:
python wallet_Master.py 50098 xxx.xxx.xxx.xxx 50082
```
### クライアント（Edgeノード）の起動

```bash:
python wallet_User.py 50093 xxx.xxx.xxx.xxx 50082
```

### クライアント（Edgeノード）の起動

```bash:
python wallet_User.py 50094 xxx.xxx.xxx.xxx 50085
```