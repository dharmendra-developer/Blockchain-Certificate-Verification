import json
import os
from web3 import Web3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABI_PATH = os.path.join(BASE_DIR, "blockchain", "contract_abi.json")

# WEB3_RPC_URL is used in cloud deployment; GANACHE_URL remains supported locally.
RPC_URL = os.getenv("WEB3_RPC_URL") or os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "").strip()
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "").strip()


class BlockchainClient:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
        self.connected = self.w3.is_connected() and bool(CONTRACT_ADDRESS)
        self.contract = None
        self.account = None

        if self.connected:
            with open(ABI_PATH, "r", encoding="utf-8") as f:
                abi = json.load(f)
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi
            )
            if PRIVATE_KEY:
                self.account = self.w3.eth.account.from_key(PRIVATE_KEY)

    def status(self):
        return {
            "connected": self.connected,
            "network": "Configured RPC endpoint" if self.w3.is_connected() else "Disconnected",
            "contract": CONTRACT_ADDRESS or "Not configured",
            "can_issue": bool(self.connected and self.account),
        }

    def issue_certificate(self, certificate_id, cert_hash):
        if not self.connected or self.contract is None:
            raise RuntimeError("Blockchain is not connected or contract is not configured.")
        if self.account is None:
            raise RuntimeError("PRIVATE_KEY is missing. Configure a dedicated Sepolia test wallet.")

        nonce = self.w3.eth.get_transaction_count(self.account.address, "pending")
        tx = self.contract.functions.issueCertificate(
            certificate_id, cert_hash
        ).build_transaction({
            "from": self.account.address,
            "nonce": nonce,
            "chainId": self.w3.eth.chain_id,
            "gas": 300000,
            "gasPrice": self.w3.eth.gas_price,
        })
        signed = self.w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError("Blockchain transaction was reverted.")
        return receipt.transactionHash.hex()

    def get_certificate(self, certificate_id):
        if not self.connected or self.contract is None:
            raise RuntimeError("Blockchain is not connected or contract is not configured.")
        data = self.contract.functions.getCertificate(certificate_id).call()
        return {
            "certificateId": data[0],
            "certificateHash": data[1],
            "issuer": data[2],
            "timestamp": data[3],
            "exists": data[4],
        }
