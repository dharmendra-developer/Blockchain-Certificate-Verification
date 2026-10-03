# Viva Questions and Answers

1. What is blockchain?
Blockchain is a distributed ledger technology in which records are linked cryptographically and replicated across participating nodes.

2. Why is blockchain used here?
To preserve a verifiable certificate fingerprint and make unauthorized modification detectable.

3. What is a smart contract?
A program deployed on a blockchain that executes defined rules and stores state.

4. Which language is used for the smart contract?
Solidity.

5. What is Ganache?
A local Ethereum-compatible development blockchain used for testing.

6. Why use SHA-256?
It produces a fixed-length fingerprint; a change in the input normally produces a different hash.

7. What does the blockchain store?
This prototype stores the certificate ID, certificate hash, issuer address, timestamp and existence flag.

8. Why not store the whole certificate on-chain?
On-chain storage is expensive and can expose personal information. A hash is sufficient for integrity verification.

9. What is Web3.py?
A Python library for communicating with Ethereum-compatible networks.

10. What is Flask?
A lightweight Python web framework used to build the application.

11. Why SQLite?
It is simple, local, lightweight and suitable for an academic prototype.

12. What is QR verification?
A QR code contains a verification URL so a user can quickly open the certificate verification page.

13. What happens if certificate data changes?
Its recalculated hash will differ from the registered blockchain hash, allowing the system to flag a mismatch.

14. Can blockchain prove that a certificate is genuine?
It can prove that the verified data matches the registered blockchain fingerprint; institutional issuance and identity controls are still required.

15. What is the role of the issuer address?
It records the blockchain account that submitted the certificate transaction.

16. What is immutability?
After a blockchain record is confirmed, altering historical state is designed to be difficult without controlling the network or its consensus process.

17. What is a transaction hash?
A unique identifier for a blockchain transaction.

18. What are the limitations of this prototype?
It uses a local blockchain, minimal authentication and no production key-management system.

19. How can the project be improved?
Use IPFS, issuer signatures, role-based access, revocation, cloud infrastructure and stronger identity controls.

20. Explain the complete workflow.
Admin enters details → hash generated → smart contract transaction → SQLite record saved → QR generated → verifier scans QR → application compares the record with blockchain state.
