// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title BlockCertMultiAuthority
/// @notice Multi-institute certificate registry for the BlockCert platform.
/// @dev A platform-managed relayer signs transactions. Institute-level
///      authorization must ALSO be enforced by the Flask application.
contract BlockCertMultiAuthority {
    address public admin;
    mapping(address => bool) public relayers;
    mapping(bytes32 => bool) public approvedAuthorities;

    struct Certificate {
        string certificateId;
        string certificateHash;
        bytes32 authorityId;
        address relayer;
        uint256 issuedAt;
        bool exists;
        bool revoked;
    }

    mapping(string => Certificate) private certificates;

    event AdminTransferred(address indexed previousAdmin, address indexed newAdmin);
    event RelayerUpdated(address indexed relayer, bool enabled);
    event AuthorityStatusChanged(bytes32 indexed authorityId, bool approved);
    event CertificateIssued(
        string indexed certificateId,
        string certificateHash,
        bytes32 indexed authorityId,
        address indexed relayer,
        uint256 issuedAt
    );
    event CertificateRevoked(
        string indexed certificateId,
        bytes32 indexed authorityId,
        address indexed relayer,
        uint256 revokedAt
    );

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only platform admin");
        _;
    }

    modifier onlyRelayer() {
        require(relayers[msg.sender], "Only platform relayer");
        _;
    }

    constructor() {
        admin = msg.sender;
        relayers[msg.sender] = true;
        emit RelayerUpdated(msg.sender, true);
        emit AdminTransferred(address(0), msg.sender);
    }

    function transferAdmin(address newAdmin) external onlyAdmin {
        require(newAdmin != address(0), "Invalid admin");
        address previous = admin;
        admin = newAdmin;
        emit AdminTransferred(previous, newAdmin);
    }

    function setRelayer(address relayer, bool enabled) external onlyAdmin {
        require(relayer != address(0), "Invalid relayer");
        relayers[relayer] = enabled;
        emit RelayerUpdated(relayer, enabled);
    }

    /// @notice authorityId should be a keccak256 hash of an internal institute UUID,
    ///         not a name, email, registration number, or other personal data.
    function setAuthorityStatus(bytes32 authorityId, bool approved) external onlyAdmin {
        require(authorityId != bytes32(0), "Invalid authority ID");
        approvedAuthorities[authorityId] = approved;
        emit AuthorityStatusChanged(authorityId, approved);
    }

    function issueCertificate(
        string calldata certificateId,
        string calldata certificateHash,
        bytes32 authorityId
    ) external onlyRelayer {
        require(bytes(certificateId).length > 0, "Certificate ID required");
        require(bytes(certificateHash).length == 64, "Expected SHA-256 hex hash");
        require(authorityId != bytes32(0), "Authority ID required");
        require(approvedAuthorities[authorityId], "Authority not approved");
        require(!certificates[certificateId].exists, "Certificate already exists");

        certificates[certificateId] = Certificate({
            certificateId: certificateId,
            certificateHash: certificateHash,
            authorityId: authorityId,
            relayer: msg.sender,
            issuedAt: block.timestamp,
            exists: true,
            revoked: false
        });

        emit CertificateIssued(
            certificateId,
            certificateHash,
            authorityId,
            msg.sender,
            block.timestamp
        );
    }

    function revokeCertificate(string calldata certificateId) external onlyRelayer {
        Certificate storage cert = certificates[certificateId];
        require(cert.exists, "Certificate not found");
        require(!cert.revoked, "Certificate already revoked");

        cert.revoked = true;
        emit CertificateRevoked(
            certificateId,
            cert.authorityId,
            msg.sender,
            block.timestamp
        );
    }

    function getCertificate(string calldata certificateId)
        external
        view
        returns (
            string memory,
            string memory,
            bytes32,
            address,
            uint256,
            bool,
            bool
        )
    {
        Certificate storage cert = certificates[certificateId];
        return (
            cert.certificateId,
            cert.certificateHash,
            cert.authorityId,
            cert.relayer,
            cert.issuedAt,
            cert.exists,
            cert.revoked
        );
    }

    function verifyCertificate(string calldata certificateId, string calldata suppliedHash)
        external
        view
        returns (bool)
    {
        Certificate storage cert = certificates[certificateId];
        return cert.exists
            && !cert.revoked
            && keccak256(bytes(cert.certificateHash)) == keccak256(bytes(suppliedHash));
    }
}
