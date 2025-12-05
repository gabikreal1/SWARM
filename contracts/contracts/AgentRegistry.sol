// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

contract AgentRegistry is Ownable {
    enum Status {
        Unregistered,
        Active,
        Inactive,
        Banned
    }

    struct Agent {
        string name;
        string metadataURI;
        string[] capabilities;
        uint256 reputation;
        Status status;
        uint256 createdAt;
        uint256 updatedAt;
    }

    mapping(address => Agent) private agents;
    address[] private agentIndex;
    mapping(address => bool) private isIndexed;

    address public reputationOracle;

    event AgentRegistered(address indexed wallet, string name, string metadataURI);
    event AgentUpdated(address indexed wallet, Status status);
    event ReputationOracleUpdated(address indexed oracle);
    event ReputationSynced(address indexed wallet, uint256 reputation);

    modifier onlyReputationOracle() {
        require(msg.sender == reputationOracle, "AgentRegistry: not reputation oracle");
        _;
    }

    constructor(address initialOwner) Ownable(initialOwner) {
        reputationOracle = initialOwner;
    }

    function registerAgent(
        string calldata name,
        string calldata metadataURI,
        string[] calldata capabilities
    ) external {
        Agent storage profile = agents[msg.sender];
        require(profile.status == Status.Unregistered, "AgentRegistry: already registered");

        profile.name = name;
        profile.metadataURI = metadataURI;
        _setCapabilities(profile, capabilities);
        profile.status = Status.Active;
        profile.createdAt = block.timestamp;
        profile.updatedAt = block.timestamp;

        if (!isIndexed[msg.sender]) {
            agentIndex.push(msg.sender);
            isIndexed[msg.sender] = true;
        }

        emit AgentRegistered(msg.sender, name, metadataURI);
    }

    function updateAgent(
        string calldata name,
        string calldata metadataURI,
        string[] calldata capabilities,
        Status status
    ) external {
        Agent storage profile = agents[msg.sender];
        require(profile.status != Status.Unregistered, "AgentRegistry: not registered");
        require(status != Status.Unregistered, "AgentRegistry: invalid status");

        profile.name = name;
        profile.metadataURI = metadataURI;
        _setCapabilities(profile, capabilities);
        profile.status = status;
        profile.updatedAt = block.timestamp;

        emit AgentUpdated(msg.sender, status);
    }

    function adminUpdateStatus(address agent, Status status) external onlyOwner {
        Agent storage profile = agents[agent];
        require(profile.status != Status.Unregistered, "AgentRegistry: not registered");
        profile.status = status;
        profile.updatedAt = block.timestamp;
        emit AgentUpdated(agent, status);
    }

    function setReputationOracle(address oracle) external onlyOwner {
        reputationOracle = oracle;
        emit ReputationOracleUpdated(oracle);
    }

    function syncReputation(address agent, uint256 reputation) external onlyReputationOracle {
        Agent storage profile = agents[agent];
        require(profile.status != Status.Unregistered, "AgentRegistry: not registered");
        profile.reputation = reputation;
        profile.updatedAt = block.timestamp;
        emit ReputationSynced(agent, reputation);
    }

    function getAgent(address wallet) external view returns (Agent memory) {
        return agents[wallet];
    }

    function getAgents(uint256 offset, uint256 limit) external view returns (Agent[] memory list, uint256 total) {
        total = agentIndex.length;
        if (offset >= total) {
            return (new Agent[](0), total);
        }

        uint256 end = offset + limit;
        if (end > total) {
            end = total;
        }

        list = new Agent[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            list[i - offset] = agents[agentIndex[i]];
        }
    }

    function getAllAgents() external view returns (Agent[] memory list) {
        list = new Agent[](agentIndex.length);
        for (uint256 i = 0; i < agentIndex.length; i++) {
            list[i] = agents[agentIndex[i]];
        }
    }

    function isAgentActive(address wallet) external view returns (bool) {
        return agents[wallet].status == Status.Active;
    }

    function agentCount() external view returns (uint256) {
        return agentIndex.length;
    }

    function _setCapabilities(Agent storage profile, string[] calldata capabilities) internal {
        delete profile.capabilities;
        for (uint256 i = 0; i < capabilities.length; i++) {
            profile.capabilities.push(capabilities[i]);
        }
    }
}
