// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./JobTypes.sol";

interface IJobRegistry {
    function upsertJob(JobTypes.JobMetadata memory job, JobTypes.JobStatus status) external;
    function updateJobStatus(uint256 jobId, JobTypes.JobStatus status) external;
    function indexBid(JobTypes.BidMetadata memory bid) external;
    function indexDelivery(JobTypes.DeliveryReceipt memory receipt) external;
}

interface IEscrow {
    function lockFunds(uint256 jobId, address user, address agent, uint256 amount) external;
    function releasePayment(uint256 jobId) external;
    function refund(uint256 jobId) external;
}

interface IReputationToken {
    function scoreOf(address agent) external view returns (uint256);
}

interface IAgentRegistryView {
    function isAgentActive(address wallet) external view returns (bool);
}

contract OrderBook is Ownable {
    using JobTypes for JobTypes.JobStatus;

    enum DisputeStatus {
        NONE,
        PENDING,
        UNDER_REVIEW,
        RESOLVED_USER,
        RESOLVED_AGENT,
        DISMISSED
    }

    struct JobState {
        address poster;
        JobTypes.JobStatus status;
        uint256 acceptedBidId;
        bytes32 deliveryProof;
        bool hasDispute;
    }

    struct Bid {
        uint256 id;
        uint256 jobId;
        address bidder;
        uint256 price;
        uint64 deliveryTime;
        uint256 reputation;
        string metadataURI;        // Agent's bid details (includes questions)
        string responseURI;        // Poster's answers to agent's questions
        bool accepted;
        uint256 createdAt;
    }

    struct Dispute {
        uint256 disputeId;
        uint256 jobId;
        address initiator;
        string reason;
        string[] evidence;
        DisputeStatus status;
        string resolutionMessage;
        uint256 createdAt;
        uint256 resolvedAt;
    }

    uint256 private nextJobId = 1;
    uint256 private nextBidId = 1;
    uint256 private nextDisputeId = 1;

    mapping(uint256 => JobState) private jobStates;
    mapping(uint256 => Bid) private bidsById;
    mapping(uint256 => uint256[]) private jobBidIds;
    mapping(uint256 => mapping(address => bool)) private agentHasBid;
    mapping(uint256 => Dispute) private disputes;
    mapping(uint256 => uint256) private jobToDispute;

    IJobRegistry public jobRegistry;
    IEscrow public escrow;
    IReputationToken public reputationToken;
    IAgentRegistryView public agentRegistry;

    event JobPosted(uint256 indexed jobId, address indexed poster);
    event BidPlaced(uint256 indexed jobId, uint256 indexed bidId, address bidder, uint256 price);
    event BidAccepted(uint256 indexed jobId, uint256 indexed bidId, address poster, address agent);
    event BidResponseSubmitted(uint256 indexed jobId, uint256 indexed bidId, string responseURI);
    event DeliverySubmitted(uint256 indexed jobId, uint256 indexed bidId, bytes32 proofHash);
    event JobApproved(uint256 indexed jobId, uint256 indexed bidId);
    event DisputeRaised(uint256 indexed disputeId, uint256 indexed jobId, address indexed initiator, string reason);
    event EvidenceSubmitted(uint256 indexed disputeId, address indexed submitter, string evidence);
    event DisputeResolved(uint256 indexed disputeId, uint256 indexed jobId, DisputeStatus resolution, string message);

    constructor(address initialOwner, IJobRegistry registry) Ownable(initialOwner) {
        jobRegistry = registry;
    }

    function setEscrow(address escrowAddress) external onlyOwner {
        escrow = IEscrow(escrowAddress);
    }

    function setReputationToken(address reputationAddress) external onlyOwner {
        reputationToken = IReputationToken(reputationAddress);
    }

    function setAgentRegistry(address registry) external onlyOwner {
        agentRegistry = IAgentRegistryView(registry);
    }

    function postJob(
        string calldata description,
        string calldata metadataURI,
        string[] calldata tags,
        uint64 deadline
    ) external returns (uint256 jobId) {
        jobId = nextJobId++;
        jobStates[jobId] = JobState({
            poster: msg.sender,
            status: JobTypes.JobStatus.OPEN,
            acceptedBidId: 0,
            deliveryProof: bytes32(0),
            hasDispute: false
        });

        string[] memory tagsCopy = tags;
        JobTypes.JobMetadata memory meta = JobTypes.JobMetadata({
            id: jobId,
            poster: msg.sender,
            description: description,
            metadataURI: metadataURI,
            tags: tagsCopy,
            deadline: deadline,
            createdAt: block.timestamp
        });
        jobRegistry.upsertJob(meta, JobTypes.JobStatus.OPEN);
        emit JobPosted(jobId, msg.sender);
    }

    function placeBid(
        uint256 jobId,
        uint256 price,
        uint64 deliveryTime,
        string calldata metadataURI
    ) external returns (uint256 bidId) {
        JobState storage job = jobStates[jobId];
        require(job.poster != address(0), "OrderBook: job not found");
        require(job.status == JobTypes.JobStatus.OPEN, "OrderBook: job not open");
        require(price > 0, "OrderBook: bid price must be positive");
        require(!agentHasBid[jobId][msg.sender], "OrderBook: agent already bid on this job");
        if (address(agentRegistry) != address(0)) {
            require(agentRegistry.isAgentActive(msg.sender), "OrderBook: agent not active");
        }

        uint256 rep = address(reputationToken) != address(0)
            ? reputationToken.scoreOf(msg.sender)
            : 0;

        bidId = nextBidId++;
        Bid storage bid = bidsById[bidId];
        bid.id = bidId;
        bid.jobId = jobId;
        bid.bidder = msg.sender;
        bid.price = price;
        bid.deliveryTime = deliveryTime;
        bid.reputation = rep;
        bid.metadataURI = metadataURI;
        bid.createdAt = block.timestamp;

        jobBidIds[jobId].push(bidId);
        agentHasBid[jobId][msg.sender] = true;

        string memory metaCopy = metadataURI;
        JobTypes.BidMetadata memory indexedBid = JobTypes.BidMetadata({
            id: bidId,
            jobId: jobId,
            bidder: msg.sender,
            price: price,
            deliveryTime: deliveryTime,
            reputation: rep,
            metadataURI: metaCopy,
            accepted: false,
            createdAt: block.timestamp
        });
        jobRegistry.indexBid(indexedBid);
        emit BidPlaced(jobId, bidId, msg.sender, price);
    }

    function acceptBid(uint256 jobId, uint256 bidId, string calldata responseURI) external {
        JobState storage job = jobStates[jobId];
        require(job.poster == msg.sender, "OrderBook: not poster");
        require(job.status == JobTypes.JobStatus.OPEN, "OrderBook: job not open");

        Bid storage bid = bidsById[bidId];
        require(bid.jobId == jobId, "OrderBook: mismatched bid");
        require(!bid.accepted, "OrderBook: bid already accepted");
        require(address(escrow) != address(0), "OrderBook: escrow not set");

        bid.accepted = true;
        bid.responseURI = responseURI;  // Store poster's answers
        job.status = JobTypes.JobStatus.IN_PROGRESS;
        job.acceptedBidId = bidId;

        jobRegistry.updateJobStatus(jobId, JobTypes.JobStatus.IN_PROGRESS);
        escrow.lockFunds(jobId, msg.sender, bid.bidder, bid.price);

        emit BidAccepted(jobId, bidId, msg.sender, bid.bidder);
        if (bytes(responseURI).length > 0) {
            emit BidResponseSubmitted(jobId, bidId, responseURI);
        }
    }

    function submitDelivery(uint256 jobId, bytes32 proofHash) external {
        JobState storage job = jobStates[jobId];
        require(job.status == JobTypes.JobStatus.IN_PROGRESS, "OrderBook: job not in progress");
        Bid storage bid = bidsById[job.acceptedBidId];
        require(bid.bidder == msg.sender, "OrderBook: not winning agent");

        job.status = JobTypes.JobStatus.DELIVERED;
        job.deliveryProof = proofHash;
        jobRegistry.updateJobStatus(jobId, JobTypes.JobStatus.DELIVERED);

        JobTypes.DeliveryReceipt memory receipt = JobTypes.DeliveryReceipt({
            jobId: jobId,
            proofHash: proofHash,
            deliveredAt: block.timestamp
        });
        jobRegistry.indexDelivery(receipt);
        emit DeliverySubmitted(jobId, job.acceptedBidId, proofHash);
    }

    function approveDelivery(uint256 jobId) external {
        JobState storage job = jobStates[jobId];
        require(job.poster == msg.sender, "OrderBook: not poster");
        require(job.status == JobTypes.JobStatus.DELIVERED, "OrderBook: job not delivered");

        job.status = JobTypes.JobStatus.COMPLETED;
        jobRegistry.updateJobStatus(jobId, JobTypes.JobStatus.COMPLETED);
        escrow.releasePayment(jobId);
        emit JobApproved(jobId, job.acceptedBidId);
    }

    function refundJob(uint256 jobId) external onlyOwner {
        JobState storage job = jobStates[jobId];
        require(job.status == JobTypes.JobStatus.IN_PROGRESS || job.status == JobTypes.JobStatus.DELIVERED, "OrderBook: cannot refund");
        require(job.hasDispute, "OrderBook: no dispute raised");

        job.status = JobTypes.JobStatus.DISPUTED;
        jobRegistry.updateJobStatus(jobId, JobTypes.JobStatus.DISPUTED);
        escrow.refund(jobId);
    }

    function getJob(uint256 jobId) external view returns (JobState memory job, Bid[] memory jobBids) {
        job = jobStates[jobId];
        uint256[] storage bidIds = jobBidIds[jobId];
        jobBids = new Bid[](bidIds.length);
        for (uint256 i = 0; i < bidIds.length; i++) {
            jobBids[i] = bidsById[bidIds[i]];
        }
    }

    function raiseDispute(uint256 jobId, string calldata reason, string calldata evidence) external returns (uint256 disputeId) {
        JobState storage job = jobStates[jobId];
        require(job.poster != address(0), "OrderBook: job not found");
        require(!job.hasDispute, "OrderBook: dispute already raised");
        require(
            job.status == JobTypes.JobStatus.IN_PROGRESS || job.status == JobTypes.JobStatus.DELIVERED,
            "OrderBook: invalid status for dispute"
        );

        Bid storage acceptedBid = bidsById[job.acceptedBidId];
        require(
            msg.sender == job.poster || msg.sender == acceptedBid.bidder,
            "OrderBook: only poster or agent can raise dispute"
        );

        disputeId = nextDisputeId++;
        Dispute storage dispute = disputes[disputeId];
        dispute.disputeId = disputeId;
        dispute.jobId = jobId;
        dispute.initiator = msg.sender;
        dispute.reason = reason;
        dispute.evidence.push(evidence);
        dispute.status = DisputeStatus.PENDING;
        dispute.createdAt = block.timestamp;

        job.hasDispute = true;
        jobToDispute[jobId] = disputeId;

        emit DisputeRaised(disputeId, jobId, msg.sender, reason);
    }

    function submitEvidence(uint256 disputeId, string calldata evidence) external {
        Dispute storage dispute = disputes[disputeId];
        require(dispute.status == DisputeStatus.PENDING || dispute.status == DisputeStatus.UNDER_REVIEW, "OrderBook: dispute not active");

        JobState storage job = jobStates[dispute.jobId];
        Bid storage acceptedBid = bidsById[job.acceptedBidId];
        require(
            msg.sender == job.poster || msg.sender == acceptedBid.bidder,
            "OrderBook: only involved parties can submit evidence"
        );

        dispute.evidence.push(evidence);
        emit EvidenceSubmitted(disputeId, msg.sender, evidence);
    }

    function resolveDispute(uint256 disputeId, DisputeStatus resolution, string calldata message) external onlyOwner {
        Dispute storage dispute = disputes[disputeId];
        require(
            dispute.status == DisputeStatus.PENDING || dispute.status == DisputeStatus.UNDER_REVIEW,
            "OrderBook: dispute already resolved"
        );
        require(
            resolution == DisputeStatus.RESOLVED_USER || 
            resolution == DisputeStatus.RESOLVED_AGENT || 
            resolution == DisputeStatus.DISMISSED,
            "OrderBook: invalid resolution status"
        );

        dispute.status = resolution;
        dispute.resolutionMessage = message;
        dispute.resolvedAt = block.timestamp;

        uint256 jobId = dispute.jobId;
        JobState storage job = jobStates[jobId];

        if (resolution == DisputeStatus.RESOLVED_USER) {
            // Refund user
            job.status = JobTypes.JobStatus.DISPUTED;
            jobRegistry.updateJobStatus(jobId, JobTypes.JobStatus.DISPUTED);
            escrow.refund(jobId);
        } else if (resolution == DisputeStatus.RESOLVED_AGENT) {
            // Release payment to agent
            job.status = JobTypes.JobStatus.COMPLETED;
            jobRegistry.updateJobStatus(jobId, JobTypes.JobStatus.COMPLETED);
            escrow.releasePayment(jobId);
        }
        // If DISMISSED, no payment action taken

        emit DisputeResolved(disputeId, jobId, resolution, message);
    }

    function getDispute(uint256 disputeId) external view returns (Dispute memory) {
        return disputes[disputeId];
    }

    function getJobDispute(uint256 jobId) external view returns (Dispute memory) {
        uint256 disputeId = jobToDispute[jobId];
        require(disputeId != 0, "OrderBook: no dispute for this job");
        return disputes[disputeId];
    }
}
