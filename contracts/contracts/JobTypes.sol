// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library JobTypes {
    enum JobStatus {
        OPEN,
        IN_PROGRESS,
        DELIVERED,
        COMPLETED,
        DISPUTED
    }

    struct JobMetadata {
        uint256 id;
        address poster;
        string description;
        string metadataURI;
        string[] tags;
        uint64 deadline;
        uint256 createdAt;
    }

    struct BidMetadata {
        uint256 id;
        uint256 jobId;
        address bidder;
        uint256 price;
        uint64 deliveryTime;
        uint256 reputation;
        string metadataURI;
        bool accepted;
        uint256 createdAt;
    }

    struct DeliveryReceipt {
        uint256 jobId;
        bytes32 proofHash;
        uint256 deliveredAt;
    }
}
