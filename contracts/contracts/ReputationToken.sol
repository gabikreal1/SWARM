// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

interface IAgentRegistrySync {
    function syncReputation(address agent, uint256 reputation) external;
}

contract ReputationToken is Ownable {
    struct AgentStats {
        uint64 jobsCompleted;
        uint64 jobsFailed;
        uint128 totalEarned;
        uint64 lastUpdated;
    }

    mapping(address => uint256) private scores;
    mapping(address => AgentStats) private stats;

    address public escrow;
    address public agentRegistry;

    event EscrowUpdated(address indexed escrow);
    event AgentRegistryUpdated(address indexed registry);
    event ReputationUpdated(address indexed agent, uint256 score, AgentStats stats);

    modifier onlyEscrow() {
        require(msg.sender == escrow, "Reputation: caller is not escrow");
        _;
    }

    constructor(address initialOwner) Ownable(initialOwner) {}

    function setEscrow(address newEscrow) external onlyOwner {
        escrow = newEscrow;
        emit EscrowUpdated(newEscrow);
    }

    function setAgentRegistry(address registry) external onlyOwner {
        agentRegistry = registry;
        emit AgentRegistryUpdated(registry);
    }

    function recordSuccess(address agent, uint256 payoutAmount) external onlyEscrow {
        AgentStats storage agentStat = stats[agent];
        agentStat.jobsCompleted += 1;
        agentStat.totalEarned += uint128(payoutAmount);
        agentStat.lastUpdated = uint64(block.timestamp);

        uint256 delta = payoutAmount / 1e6 + 10;
        scores[agent] += delta;

        _syncAgentRegistry(agent);
        emit ReputationUpdated(agent, scores[agent], agentStat);
    }

    function recordFailure(address agent) external onlyEscrow {
        AgentStats storage agentStat = stats[agent];
        agentStat.jobsFailed += 1;
        agentStat.lastUpdated = uint64(block.timestamp);

        if (scores[agent] > 5) {
            scores[agent] -= 5;
        } else {
            scores[agent] = 0;
        }

        _syncAgentRegistry(agent);
        emit ReputationUpdated(agent, scores[agent], agentStat);
    }

    function scoreOf(address agent) external view returns (uint256) {
        return scores[agent];
    }

    function statsOf(address agent) external view returns (AgentStats memory) {
        return stats[agent];
    }

    function _syncAgentRegistry(address agent) internal {
        if (agentRegistry != address(0)) {
            IAgentRegistrySync(agentRegistry).syncReputation(agent, scores[agent]);
        }
    }
}
