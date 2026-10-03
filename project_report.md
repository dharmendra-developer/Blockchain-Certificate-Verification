# Blockchain-Based Certificate Verification and Management System

## Abstract
This project presents a blockchain-based certificate verification platform designed to reduce certificate forgery and simplify verification. The application uses Flask as the web layer, SQLite as the local application database, SHA-256 as a document fingerprinting mechanism, Solidity for the smart contract, Ganache as a local Ethereum-compatible blockchain, Web3.py for blockchain communication, and QR codes for convenient verification.

## 1. Introduction
Traditional certificate verification can require manual checking and communication with the issuing institution. Digitally stored records can also be altered if the storage system is compromised. Blockchain provides an append-oriented, distributed record layer that can be used to preserve a certificate fingerprint.

## 2. Problem Statement
Institutions need a simple method to issue and verify certificates while detecting changes to stored certificate information.

## 3. Objectives
- Generate a unique certificate ID.
- Create a SHA-256 fingerprint from certificate data.
- Register the fingerprint on an Ethereum-compatible blockchain.
- Store application-level details in SQLite.
- Generate a QR code for verification.
- Compare the database fingerprint with the blockchain fingerprint.

## 4. Scope
The prototype is intended for academic demonstration and local testing. A production system would require authentication, access control, privacy design, secure key management, certificate revocation, monitoring, and deployment hardening.

## 5. Technology Stack
Python, Flask, SQLite, Solidity, Ethereum-compatible blockchain, Ganache, Web3.py, HTML, CSS, JavaScript, SHA-256, QR Code.

## 6. System Architecture
User → Flask Web UI → SHA-256 Hash → SQLite
                         ↘ Web3.py → Smart Contract → Ganache
                         ↘ QR Generator → Verification URL

## 7. Modules
### Certificate Issuance
Captures student and certificate details and creates a certificate ID.

### Hashing
Canonicalizes the certificate fields and creates a SHA-256 fingerprint.

### Blockchain Registration
Calls `issueCertificate()` in the Solidity contract.

### Database
SQLite stores application data, hash, transaction hash, and QR filename.

### QR Verification
The QR encodes the verification URL containing the certificate ID.

### Verification
The application reads the local record and blockchain record and compares hashes.

## 8. Smart Contract
The contract maintains a mapping from certificate ID to certificate hash, issuer address, timestamp, and existence flag. Duplicate certificate IDs are rejected.

## 9. Security Concepts
- Hash integrity
- Blockchain immutability properties
- Smart-contract state
- QR-based lookup
- Separation of on-chain hash from application data

## 10. Advantages
- Faster verification
- Tamper-evident fingerprint
- Simple QR-based access
- Reduced manual verification effort
- Transparent technical architecture for demonstration

## 11. Limitations
- Local Ganache is not a production blockchain.
- A hash proves consistency of the hashed fields, not that the original information was truthful.
- Lost or compromised issuer keys can create operational risk.
- The prototype has minimal authentication.
- QR codes can be copied, so the verification endpoint must remain authoritative.

## 12. Future Scope
- IPFS certificate storage
- Digital signatures
- Issuer authorization
- Certificate revocation
- Role-based access
- Cloud deployment
- Mobile verification app
- Multi-institution network

## 13. Conclusion
The project demonstrates how blockchain can complement conventional web applications by storing a verifiable fingerprint rather than the complete certificate. The combination of Flask, SQLite, Solidity, Web3.py and QR verification creates an understandable and extensible CSE academic prototype.
