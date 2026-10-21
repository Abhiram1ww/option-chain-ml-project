from kiteconnect import KiteConnect

api_key = ""
api_secret = ""
request_token = ""

kite = KiteConnect(api_key=api_key)

data = kite.generate_session(
    request_token=request_token,
    api_secret=api_secret
)

print("ACCESS TOKEN:")
print(data["access_token"])
