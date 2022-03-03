### Tested System:
* OSX 10.12.6
* python 3.8.10

* 始原Coreノードにつなぐためのサーバ

### サーバー２の起動

```bash:
python system_server.py 50085 xxx.xxx.xxx.xxx 50082 test
```

### サーバー3の起動

```bash:
python system_server.py 50088 xxx.xxx.xxx.xxx 50085 test
```