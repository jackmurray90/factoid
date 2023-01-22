from bitcoinrpc.authproxy import AuthServiceProxy
from config import BITCOIN
from time import sleep

def validate_address(address):
  while True:
    try:
      rpc = AuthServiceProxy(BITCOIN)
      return rpc.validateaddress(address)['isvalid']
    except:
      sleep(1)
