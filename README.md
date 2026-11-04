# 🔐 BlockCert — Blockchain Certificate Verification System

> **A secure, tamper-resistant certificate issuance and verification platform powered by Blockchain, Flask, Solidity, and QR Codes.**

**BlockCert** is a CSE academic project designed to demonstrate how blockchain technology can be used to issue, store, and verify digital certificates. The system generates a unique **SHA-256 certificate hash**, stores the fingerprint on an Ethereum-compatible blockchain, maintains an SQLite audit record, and provides a **QR-code-based verification system**.

---

## 📌 Project Overview

Traditional certificate verification can be time-consuming and certificates may be vulnerable to alteration or forgery.

BlockCert addresses this problem by combining:

* 🐍 Flask web application
* ⛓️ Ethereum-compatible blockchain
* 📜 Solidity smart contract
* 🔑 SHA-256 certificate hashing
* 🗄️ SQLite database
* 📱 QR-code verification
* 🌐 Web-based verification
* 🔌 Web3.py blockchain integration
* 🖥️ Ganache local blockchain

The actual certificate PDF is **not stored on the blockchain**. Instead, a cryptographic fingerprint of the certificate data is stored. During verification, the generated hash is compared with the blockchain record.

---

## ✨ Features

### 🎓 Certificate Management

* Certificate issuance form
* Student information management
* Course/program details
* Institute information
* Issue date and program duration
* Program description

### 🔐 Certificate Authority Authentication

* Protected certificate issuance
* Authority login
* Session-based authentication
* Configurable username and password

### ⛓️ Blockchain Integration

* Solidity smart contract
* Ethereum-compatible blockchain
* Ganache local development network
* Web3.py integration
* Blockchain transaction hash recording

### 🔒 Certificate Security

* Canonical certificate JSON
* SHA-256 certificate fingerprint
* Tamper detection
* Blockchain-backed verification

### 📱 QR Verification

* Automatic QR-code generation
* QR code included with certificate
* Scan QR using mobile device
* Direct verification URL

### 🌐 Verification System

* Public certificate verification page
* Certificate hash verification
* JSON verification API
* Blockchain transaction information

### 🗄️ Database

* SQLite database
* Certificate audit records
* Transaction hash storage
* Certificate metadata

### 📴 Local/Demo Mode

The application can still run when blockchain configuration is unavailable, allowing demonstration of the Flask UI, database, certificate generation, and QR workflow.

---

# 🏗️ System Architecture

```text
                  ┌──────────────────────┐
                  │      Certificate     │
                  │       Authority      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │     Flask Web App    │
                  │       Backend        │
                  └──────────┬───────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
                ▼            ▼            ▼
        ┌────────────┐ ┌──────────┐ ┌──────────────┐
        │ SHA-256    │ │  SQLite  │ │ Certificate  │
        │   Hash     │ │ Database │ │     PDF      │
        └─────┬──────┘ └──────────┘ └──────┬───────┘
              │                             │
              ▼                             ▼
        ┌───────────────┐            ┌──────────────┐
        │ Solidity      │            │ QR Generator │
        │ Smart Contract│            └──────┬───────┘
        └───────┬───────┘                   │
                │                           ▼
                ▼                    ┌──────────────┐
        ┌──────────────┐             │ Verification │
        │   Ganache    │             │     URL      │
        │  Blockchain  │             └──────┬───────┘
        └──────────────┘                    │
                                            ▼
                                    ┌────────────────┐
                                    │ Student /      │
                                    │ Verifier       │
                                    └────────────────┘
```

---

# 🔄 Certificate Workflow

```text
Authority Login
       │
       ▼
Issue Certificate
       │
       ▼
Create Canonical JSON
       │
       ▼
Generate SHA-256 Hash
       │
       ▼
Store Hash on Blockchain
       │
       ▼
Store Audit Record in SQLite
       │
       ▼
Generate Certificate PDF
       │
       ▼
Generate QR Code
       │
       ▼
Student Receives Certificate
       │
       ▼
Verifier Scans QR
       │
       ▼
Verification Page
       │
       ▼
Compare Certificate Hash
       │
       ▼
Valid / Invalid
```

---

# 🛠️ Technology Stack

| Technology    | Purpose                    |
| ------------- | -------------------------- |
| Python        | Application development    |
| Flask         | Web framework              |
| SQLite        | Local database             |
| Solidity      | Smart contract             |
| Web3.py       | Blockchain communication   |
| Ganache       | Local Ethereum blockchain  |
| SHA-256       | Certificate fingerprinting |
| QR Code       | Certificate verification   |
| HTML5         | Frontend structure         |
| CSS3          | UI styling                 |
| JavaScript    | Frontend interactions      |
| PDF Generator | Certificate generation     |

---

# 📁 Project Structure

```text
BlockCert/
│
├── app.py
├── requirements.txt
├── README.md
│
├── contracts/
│   └── CertificateVerification.sol
│
├── blockchain/
│   └── contract_abi.json
│
├── database/
│   └── certificates.db
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── issue_certificate.html
│   ├── certificate.html
│   └── verify.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   └── images/
│
├── certificates/
│   └── generated/
│
└── qr_codes/
    └── generated/
```

> Your actual folder structure may vary depending on the implementation.

---

# 💻 Requirements

Before running BlockCert, install:

* Python **3.10 or higher**
* Node.js
* Ganache
* Modern web browser
* Optional: Remix IDE

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/blockcert.git
cd blockcert
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# ⛓️ Blockchain Setup

## 1. Start Ganache

Open Ganache and create a workspace.

Use:

```text
RPC URL:
http://127.0.0.1:7545
```

Make sure Ganache is running before starting the Flask application.

---

## 2. Copy Ganache Account

Copy one funded account address from Ganache.

The account will be used by the application to send blockchain transactions.

---

# 📜 Smart Contract Deployment

Open:

```text
contracts/CertificateVerification.sol
```

using Remix IDE.

### Recommended Compiler

```text
Solidity: 0.8.20
```

or another compatible Solidity `0.8.x` compiler.

### Deployment

1. Open Remix.
2. Add `CertificateVerification.sol`.
3. Compile the contract.
4. Select the appropriate Ganache provider.
5. Deploy `CertificateVerification`.
6. Copy the deployed contract address.
7. Export/copy the generated ABI.

Save the ABI as:

```text
blockchain/contract_abi.json
```

---

# 🔧 Environment Configuration

## Windows CMD

```cmd
set CONTRACT_ADDRESS=YOUR_CONTRACT_ADDRESS
set GANACHE_URL=http://127.0.0.1:7545
```

## Windows PowerShell

```powershell
$env:CONTRACT_ADDRESS="YOUR_CONTRACT_ADDRESS"
$env:GANACHE_URL="http://127.0.0.1:7545"
```

### Linux/macOS

```bash
export CONTRACT_ADDRESS="YOUR_CONTRACT_ADDRESS"
export GANACHE_URL="http://127.0.0.1:7545"
```

---

# 🔐 Certificate Authority Login

For local demonstration, the default credentials are:

```text
Username: authority
Password: Authority@123
```

For actual use, configure your own credentials.

### PowerShell

```powershell
$env:ADMIN_USERNAME="your-authority-name"
$env:ADMIN_PASSWORD="your-strong-password"
$env:FLASK_SECRET_KEY="your-long-random-secret"
```

Then start the application.

> ⚠️ Never commit real passwords, private keys, wallet credentials, or production secret keys to GitHub.

---

# ▶️ Run the Application

Start Flask:

```bash
python app.py
```

Open your browser:

```text
http://127.0.0.1:5000
```

---

# 🧾 Issuing a Certificate

The certificate authority follows these steps:

1. Login as Certificate Authority.
2. Open **Issue Certificate**.
3. Enter student information.
4. Enter course/program details.
5. Enter institute information.
6. Enter issue date.
7. Enter program start/end dates.
8. Add program description.
9. Submit the certificate.
10. Flask generates a canonical certificate payload.
11. SHA-256 generates the certificate fingerprint.
12. The fingerprint is submitted to the smart contract.
13. SQLite stores the audit record.
14. Certificate PDF is generated.
15. QR code is generated.
16. QR code is added to the certificate.

---

# 🔍 Certificate Verification

A verifier can scan the QR code printed on the certificate.

The QR code opens a verification URL such as:

```text
http://127.0.0.1:5000/verify/<certificate_id>
```

The system retrieves the certificate information and compares the certificate hash with the blockchain record.

### Example Result

```text
Certificate: Valid
Blockchain Record: Found
Hash Status: Matched
Transaction: Confirmed
```

If the certificate information has been modified:

```text
Certificate: Invalid
Hash Status: Mismatch
```

---

# 🔑 SHA-256 Certificate Hashing

BlockCert creates a canonical representation of the certificate data.

Example:

```json
{
    "student_name": "Rahul Kumar",
    "course": "Diploma in Computer Science",
    "institute": "Government Polytechnic",
    "issue_date": "2026-10-03"
}
```

The canonical data is passed through SHA-256.

```text
Certificate Data
       │
       ▼
Canonical JSON
       │
       ▼
SHA-256
       │
       ▼
Certificate Fingerprint
```

The fingerprint is then stored on the blockchain.

---

# ⛓️ Blockchain Data

The blockchain stores the certificate fingerprint and required verification metadata rather than the complete PDF.

Conceptually:

```text
Certificate ID
      +
Certificate Hash
      +
Issuer Information
      +
Timestamp
      ↓
Smart Contract
      ↓
Blockchain
```

This keeps the on-chain data relatively small while allowing later integrity verification.

---

# 📱 QR Code Verification

The QR code contains a verification URL.

```text
Certificate PDF
       │
       ▼
    QR Code
       │
       ▼
Mobile Camera
       │
       ▼
Verification URL
       │
       ▼
Flask Verification Page
       │
       ▼
Blockchain Hash Check
```

---

# 🌐 Verification API

BlockCert also provides a JSON verification API.

Example:

```text
GET /api/verify/<certificate_id>
```

Example response:

```json
{
    "valid": true,
    "certificate_id": "CERT-001",
    "hash_match": true,
    "blockchain_verified": true
}
```

The exact response fields depend on the implementation.

---

# 🗄️ SQLite Audit Database

SQLite maintains an application-side record of certificate issuance.

Typical information includes:

```text
Certificate ID
Student Name
Course
Institute
Issue Date
Certificate Hash
Blockchain Transaction Hash
Created At
```

The database provides an application audit trail while the blockchain provides tamper-evident certificate fingerprint storage.

---

# 🔒 Security Model

BlockCert uses multiple security mechanisms:

### 1. Authentication

Only authenticated certificate authorities can issue certificates.

### 2. SHA-256

Each certificate receives a cryptographic fingerprint.

### 3. Blockchain

The fingerprint is recorded on an Ethereum-compatible blockchain.

### 4. QR Verification

A verifier can quickly access the certificate verification page.

### 5. Database Audit

SQLite maintains the application-side issuance record.

---

# 📊 Advantages

* Reduces certificate forgery risk
* Fast certificate verification
* Blockchain-backed integrity checking
* QR-based verification
* Digital certificate generation
* Easy local demonstration
* Low-cost academic prototype
* Clear demonstration of blockchain concepts
* Can be extended to cloud deployment

---

# ⚠️ Limitations

This project is primarily an **academic/local prototype**.

Current limitations may include:

* Ganache is intended for development/testing.
* Local blockchain data is not a production trust infrastructure.
* Private keys require secure management.
* SQLite is suitable for a prototype but may not be ideal for large-scale deployment.
* Certificate PDFs are not stored directly on-chain.
* Production deployment requires stronger authentication and authorization.
* Smart-contract security auditing would be required before production use.

---

# 🚀 Future Enhancements

Possible future improvements include:

* 👥 Role-based access control
* 🏫 Multiple certificate authorities
* ❌ Certificate revocation
* 🔄 Certificate status management
* ☁️ Cloud deployment
* 📦 IPFS certificate storage
* 🔐 Wallet-based issuer authentication
* 🧾 Certificate templates
* 📧 Email certificate delivery
* 📱 Mobile verification application
* 🔎 Advanced certificate search
* 📈 Admin dashboard and analytics
* 🛡️ Smart-contract security audit
* 🔑 Production-grade wallet/key management

---

# 🎓 Academic Use

This project demonstrates concepts from:

* Blockchain Technology
* Distributed Ledger Technology
* Smart Contracts
* Web3
* Cryptography
* Database Management Systems
* Web Development
* Software Engineering
* Cybersecurity
* QR Technology
* API Development

---

# 🧪 Testing Checklist

Before demonstrating the project, verify:

```text
☐ Python environment created
☐ Dependencies installed
☐ Ganache running
☐ RPC URL configured
☐ Smart contract deployed
☐ Contract address configured
☐ ABI configured
☐ Flask application running
☐ Authority login working
☐ Certificate generation working
☐ QR code generated
☐ Verification page working
☐ Blockchain transaction confirmed
☐ SQLite record created
☐ API verification working
```

---

# 🐛 Troubleshooting

### Ganache Connection Refused

Check that Ganache is running:

```text
http://127.0.0.1:7545
```

Also verify:

```bash
GANACHE_URL=http://127.0.0.1:7545
```

---

### Contract Address Not Configured

Set:

```powershell
$env:CONTRACT_ADDRESS="YOUR_CONTRACT_ADDRESS"
```

---

### ABI Error

Replace:

```text
blockchain/contract_abi.json
```

with the ABI generated after compiling and deploying the Solidity contract.

---

### Blockchain Unavailable

The Flask application can still demonstrate the UI/database/QR workflow when blockchain configuration is unavailable, depending on the application's configured fallback behavior.

---

# 🔮 Production Considerations

Before deploying a real-world version:

* Use HTTPS.
* Never store private keys directly in source code.
* Use secure environment variables or a dedicated key-management system.
* Implement proper role-based authorization.
* Validate and sanitize all user input.
* Add certificate revocation.
* Consider decentralized storage such as IPFS for large certificate files.
* Use a production-grade database.
* Audit the smart contract.
* Add rate limiting and security monitoring.
* Maintain secure backups.
* Protect personally identifiable information.

---

# 👨‍💻 Project Type

```text
Academic CSE Project
Blockchain + Web Development
Certificate Verification System
```

### Project Name

**BlockCert**

### Full Name

**Blockchain-Based Certificate Verification and Management System**

---

# 📜 License

This project is intended for **educational and academic purposes**.

You may modify and extend the project for learning, demonstration, and academic submission according to your institution's requirements.

---

# ⭐ Support

If you find this project useful for learning blockchain, Flask, Solidity, and Web3 development, consider giving the repository a ⭐ on GitHub.

---

## 👨‍💻 Developer

**Dharmendra Kumar Singh**

> Python Developer • AI Enthusiast • Future Software Engineer

**Project:** BlockCert — Blockchain Certificate Verification System

---

# 📌 Quick Start

For a quick local demonstration:

```bash
git clone https://github.com/YOUR_USERNAME/blockcert.git
cd blockcert

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt

python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

For blockchain verification, start Ganache and configure the deployed Solidity contract before issuing certificates.
