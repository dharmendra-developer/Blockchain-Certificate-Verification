import os
from web3 import Web3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABI_PATH = os.path.join(BASE_DIR, "blockchain", "contract_abi.json")

GANACHE_URL = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")

class BlockchainClient:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        self.connected = self.w3.is_connected() and bool(CONTRACT_ADDRESS)
        self.contract = None
        self.account = None
        if self.connected:
            with open(ABI_PATH, "r", encoding="utf-8") as f:
                abi = __import__("json").load(f)
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi
            )
            accounts = self.w3.eth.accounts
            if accounts:
                self.account = accounts[0]

    def status(self):
        return {
            "connected": self.connected,
            "network": GANACHE_URL,
            "contract": CONTRACT_ADDRESS or "Not configured"
        }

    def issue_certificate(self, certificate_id, cert_hash):
        tx = self.contract.functions.issueCertificate(
            certificate_id, cert_hash
        ).transact({"from": self.account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        return receipt["transactionHash"].hex()

    def get_certificate(self, certificate_id):
        data = self.contract.functions.getCertificate(certificate_id).call()
        return {
            "certificateId": data[0],
            "certificateHash": data[1],
            "issuer": data[2],
            "timestamp": data[3],
            "exists": data[4]
        }
