// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IReputationEmitter {
    function recordSuccess(address agent, uint256 payoutAmount) external;
    function recordFailure(address agent) external;
}

contract Escrow is Ownable, ReentrancyGuard {
    struct EscrowDeposit {
        address user;
        address agent;
        uint256 amount;
        bool funded;
        bool released;
        bool refunded;
    }

    IERC20 public immutable token;
    address public orderBook;
    address public feeCollector;
    uint96 public platformFeeBps; // e.g. 200 = 2%
    IReputationEmitter public reputation;

    mapping(uint256 => EscrowDeposit) private escrows;

    event OrderBookUpdated(address indexed orderBook);
    event ReputationUpdated(address indexed reputationContract);
    event FeeCollectorUpdated(address indexed collector, uint96 feeBps);
    event EscrowCreated(uint256 indexed jobId, address indexed user, address indexed agent, uint256 amount);
    event PaymentReleased(uint256 indexed jobId, address indexed agent, uint256 payout, uint256 fee);
    event PaymentRefunded(uint256 indexed jobId, address indexed user, uint256 amount);

    modifier onlyOrderBook() {
        require(msg.sender == orderBook, "Escrow: caller is not order book");
        _;
    }

    constructor(address initialOwner, IERC20 usdc, address initialFeeCollector) Ownable(initialOwner) {
        token = usdc;
        feeCollector = initialFeeCollector;
        platformFeeBps = 200;
    }

    function setOrderBook(address newOrderBook) external onlyOwner {
        orderBook = newOrderBook;
        emit OrderBookUpdated(newOrderBook);
    }

    function setReputation(address reputationContract) external onlyOwner {
        reputation = IReputationEmitter(reputationContract);
        emit ReputationUpdated(reputationContract);
    }

    function setFeeCollector(address collector, uint96 feeBps) external onlyOwner {
        require(feeBps <= 1_000, "Escrow: fee too high");
        feeCollector = collector;
        platformFeeBps = feeBps;
        emit FeeCollectorUpdated(collector, feeBps);
    }

    function lockFunds(uint256 jobId, address user, address agent, uint256 amount) external onlyOrderBook {
        EscrowDeposit storage escrowData = escrows[jobId];
        require(!escrowData.funded, "Escrow: already funded");

        escrowData.user = user;
        escrowData.agent = agent;
        escrowData.amount = amount;
        escrowData.funded = true;

        require(token.transferFrom(user, address(this), amount), "Escrow: transfer failed");
        emit EscrowCreated(jobId, user, agent, amount);
    }

    function releasePayment(uint256 jobId) external onlyOrderBook nonReentrant {
        EscrowDeposit storage escrowData = escrows[jobId];
        require(escrowData.funded, "Escrow: not funded");
        require(!escrowData.released, "Escrow: already released");
        require(!escrowData.refunded, "Escrow: refunded");

        escrowData.released = true;
        uint256 fee = (escrowData.amount * platformFeeBps) / 10_000;
        uint256 payout = escrowData.amount - fee;

        if (fee > 0 && feeCollector != address(0)) {
            require(token.transfer(feeCollector, fee), "Escrow: fee transfer failed");
        }
        require(token.transfer(escrowData.agent, payout), "Escrow: payout failed");

        emit PaymentReleased(jobId, escrowData.agent, payout, fee);
        if (address(reputation) != address(0)) {
            reputation.recordSuccess(escrowData.agent, escrowData.amount);
        }
    }

    function refund(uint256 jobId) external onlyOrderBook nonReentrant {
        EscrowDeposit storage escrowData = escrows[jobId];
        require(escrowData.funded, "Escrow: not funded");
        require(!escrowData.released, "Escrow: already released");
        require(!escrowData.refunded, "Escrow: already refunded");

        escrowData.refunded = true;
        require(token.transfer(escrowData.user, escrowData.amount), "Escrow: refund failed");

        emit PaymentRefunded(jobId, escrowData.user, escrowData.amount);
        if (address(reputation) != address(0)) {
            reputation.recordFailure(escrowData.agent);
        }
    }

    function getEscrow(uint256 jobId) external view returns (EscrowDeposit memory) {
        return escrows[jobId];
    }
}
