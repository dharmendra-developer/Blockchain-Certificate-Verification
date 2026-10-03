# BlockCert — Blockchain Certificate Verification System

A CSE academic project that combines Flask, SQLite, Solidity, Web3.py, Ganache, SHA-256 hashing, and QR codes.

## Features
- Admin-style certificate issuance form
- Certificate-authority login for protected certificate issuance
- Downloadable certificate PDF with verification QR code
- SHA-256 canonical certificate hash
- Ethereum-compatible smart contract
- Ganache local blockchain integration
- SQLite audit/database record
- QR code that opens verification
- Web verification page
- JSON verification API
- Works in offline/local mode if blockchain is not configured

## 1. Requirements
- Python 3.10+
- Node.js + Ganache (Ganache GUI or ganache CLI)
- A browser
- Optional: Remix IDE for easy smart-contract deployment

## 2. Install Python packages
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Start Ganache
Use Ganache GUI and create a workspace with RPC server:
`HTTP://127.0.0.1:7545`

Copy one funded account from Ganache.

## 4. Deploy Solidity contract
Open `contracts/CertificateVerification.sol` in Remix.
- Compiler: Solidity 0.8.20 or compatible 0.8.x compiler
- Environment: Injected Provider / or Ganache provider as appropriate
- Deploy `CertificateVerification`
- Copy the deployed contract address.

Then set:
```bash
set CONTRACT_ADDRESS=YOUR_ADDRESS
set GANACHE_URL=http://127.0.0.1:7545
```
PowerShell:
```powershell
$env:CONTRACT_ADDRESS="YOUR_ADDRESS"
$env:GANACHE_URL="http://127.0.0.1:7545"
```

## 5. ABI
Copy the deployed contract ABI into `blockchain/contract_abi.json`.
A placeholder ABI is included; replace it with Remix's generated ABI after deployment.

## 6. Run
```bash
python app.py
```
Open http://127.0.0.1:5000

## Certificate authority login
The local demo defaults are username `authority` and password `Authority@123`. Set your own credentials and a strong Flask session key before using the application beyond a local demo.

PowerShell:
```powershell
$env:ADMIN_USERNAME="your-authority-name"
$env:ADMIN_PASSWORD="use-a-strong-password"
$env:FLASK_SECRET_KEY="generate-a-long-random-secret"
python app.py
```

Only signed-in certificate authorities can open or submit the issuance form. Certificate viewing and verification remain public.

## Workflow
1. Open Issue Certificate.
2. Enter student, course, institute, issue date, program start/end dates, and a short program description.
3. Flask creates a canonical JSON payload.
4. SHA-256 creates the certificate fingerprint from the certificate and program details.
5. The fingerprint is sent to the smart contract.
6. SQLite stores the application record and transaction hash.
7. QR code is generated for verification.
8. Scanning the QR opens the verification URL.
9. Verification compares the stored hash with the blockchain hash.

## Important academic note
The blockchain stores the certificate hash and metadata needed for verification, not the complete certificate file. This reduces on-chain data and avoids putting unnecessary personal data on a public blockchain.

## Troubleshooting
- `Connection refused`: start Ganache and check port 7545.
- `Contract address not configured`: set CONTRACT_ADDRESS.
- `ABI error`: replace `blockchain/contract_abi.json` with the ABI exported by Remix.
- If blockchain is unavailable, the Flask app still runs and demonstrates the UI/database/QR workflow.

## Suggested future improvements
Authentication, role-based authorization, IPFS for certificate PDFs, issuer allow-list, revocation function, cloud deployment, and a production wallet/key-management strategy.
