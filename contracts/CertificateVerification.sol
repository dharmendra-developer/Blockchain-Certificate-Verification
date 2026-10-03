// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CertificateVerification {
    struct Certificate {
        string certificateId;
        string certificateHash;
        address issuer;
        uint256 timestamp;
        bool exists;
    }

    mapping(string => Certificate) private certificates;

    event CertificateIssued(
        string indexed certificateId,
        string certificateHash,
        address indexed issuer,
        uint256 timestamp
    );

    function issueCertificate(
        string memory certificateId,
        string memory certificateHash
    ) public {
        require(!certificates[certificateId].exists, "Certificate already exists");

        certificates[certificateId] = Certificate(
            certificateId,
            certificateHash,
            msg.sender,
            block.timestamp,
            true
        );

        emit CertificateIssued(
            certificateId,
            certificateHash,
            msg.sender,
            block.timestamp
        );
    }

    function getCertificate(string memory certificateId)
        public
        view
        returns (
            string memory,
            string memory,
            address,
            uint256,
            bool
        )
    {
        Certificate memory c = certificates[certificateId];
        return (
            c.certificateId,
            c.certificateHash,
            c.issuer,
            c.timestamp,
            c.exists
        );
    }
}
