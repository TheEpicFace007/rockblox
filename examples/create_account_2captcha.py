from twocaptcha import TwoCaptcha
import rockblox
import secrets

# initialize solver(2captcha) and rockblox session
solver = TwoCaptcha("API_KEY")
session = rockblox.Session()

# wait for captcha result
captcha_result = solver.funcaptcha(
    sitekey="A2A14B1D-1AF3-C791-9BBC-EE33CC7A0A6F",
    url=session.build_url("www", "/"))

# generate credentials
username = "burger9234"
password = secrets.token_hex(8)

# create account
session.signup(
    username, 
    password,
    "01 Jan 2000",
    captcha_token=captcha_result["code"],
    captcha_provider="PROVIDER_ARKOSE_LABS")

# print user name and id
print(session.name, session.id)