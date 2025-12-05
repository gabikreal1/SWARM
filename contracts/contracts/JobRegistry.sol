// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./JobTypes.sol";

contract JobRegistry is Ownable {
    using JobTypes for JobTypes.JobMetadata;

    struct StoredJob {
        JobTypes.JobMetadata metadata;
        JobTypes.JobStatus status;
        bytes32 deliveryProof;
        uint256 deliveredAt;
    }

    mapping(uint256 => StoredJob) private jobRecords;
    mapping(uint256 => JobTypes.BidMetadata[]) private jobBids;

    address public orderBook;

    event OrderBookUpdated(address indexed orderBook);
    event JobIndexed(uint256 indexed jobId, address indexed poster);
    event BidIndexed(uint256 indexed jobId, uint256 indexed bidId, address bidder);
    event DeliveryIndexed(uint256 indexed jobId, bytes32 proofHash);

    modifier onlyOrderBook() {
        require(msg.sender == orderBook, "JobRegistry: caller is not order book");
        _;
    }

    constructor(address initialOwner) Ownable(initialOwner) {}

    function setOrderBook(address newOrderBook) external onlyOwner {
        orderBook = newOrderBook;
        emit OrderBookUpdated(newOrderBook);
    }

    function upsertJob(JobTypes.JobMetadata memory job, JobTypes.JobStatus status) external onlyOrderBook {
        StoredJob storage record = jobRecords[job.id];
        record.metadata.id = job.id;
        record.metadata.poster = job.poster;
        record.metadata.description = job.description;
        record.metadata.metadataURI = job.metadataURI;
        _copyStrings(job.tags, record.metadata.tags);
        record.metadata.deadline = job.deadline;
        record.metadata.createdAt = job.createdAt;
        record.status = status;

        emit JobIndexed(job.id, job.poster);
    }

    function updateJobStatus(uint256 jobId, JobTypes.JobStatus status) external onlyOrderBook {
        jobRecords[jobId].status = status;
    }

    function indexBid(JobTypes.BidMetadata memory bid) external onlyOrderBook {
        jobBids[bid.jobId].push(bid);
        emit BidIndexed(bid.jobId, bid.id, bid.bidder);
    }

    function indexDelivery(JobTypes.DeliveryReceipt memory receipt) external onlyOrderBook {
        StoredJob storage record = jobRecords[receipt.jobId];
        record.deliveryProof = receipt.proofHash;
        record.deliveredAt = receipt.deliveredAt;
        emit DeliveryIndexed(receipt.jobId, receipt.proofHash);
    }

    function getJob(uint256 jobId)
        external
        view
        returns (StoredJob memory job, JobTypes.BidMetadata[] memory bids)
    {
        job = jobRecords[jobId];
        bids = jobBids[jobId];
    }

    function getBids(uint256 jobId) external view returns (JobTypes.BidMetadata[] memory bids) {
        bids = jobBids[jobId];
    }

    function _copyStrings(string[] memory source, string[] storage target) internal {
        while (target.length > 0) {
            target.pop();
        }
        for (uint256 i = 0; i < source.length; i++) {
            target.push(source[i]);
        }
    }
}
