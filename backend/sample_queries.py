import json
import sys
from typing import Optional

import requests

API = 'http://127.0.0.1:8000'

def call(msg: str, sid: Optional[str] = None) -> str:
  r = requests.post(f"{API}/chat", json={"message": msg, "session_id": sid})
  r.raise_for_status()
  data = r.json()
  print(json.dumps(data, indent=2))
  return data["session_id"]

if __name__ == '__main__':
  sid = call("I lost my credit card, my address is 123 Main St, please replace it")
  sid = call("debit", sid)
  sid = call("it's lost", sid)
  sid = call("check my balance for account number 123456 with token ABCD")
  sid = call("transfer 99 from 111111 to 222222", sid) 