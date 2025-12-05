"""
Example SpoonOS Agent for NeoxPrep Marketplace
This agent demonstrates how to import and use the contract environment module.
"""

import json
import subprocess
import os
from typing import Dict, List, Optional


class NeoxPrepSpoonAgent:
    """
    SpoonOS agent that interacts with the NeoxPrep marketplace contracts.
    """

    def __init__(self, env_mode: str = "read_only"):
        """
        Initialize the agent.

        Args:
            env_mode: "read_only" (no private key) or "write" (with private key)
        """
        self.env_mode = env_mode
        self.contracts_dir = "contracts"  # Relative to where this runs
        self.env = self._load_spoon_env()

        if not self.env:
            raise RuntimeError("Failed to load SpoonOS environment")

        self.addresses = self.env.get("ContractAddresses", {})
        self.abis = self.env.get("ABIs", {})

    def _load_spoon_env(self) -> Dict:
        """Load contract metadata from the TypeScript SpoonOS env module."""
        try:
            # Run the spoonos-env.ts module and capture JSON output
            result = subprocess.run(
                [
                    "npx",
                    "ts-node",
                    "--files",
                    "integrations/spoon/spoonos-env.ts",
                ],
                capture_output=True,
                text=True,
                cwd=self.contracts_dir,
                timeout=30,
            )

            if result.returncode != 0:
                print(f"Error loading env: {result.stderr}")
                return {}

            # Try to parse the output as JSON
            # (Note: spoonos-env.ts should export a JSON structure)
            output = result.stdout.strip()
            if output:
                return json.loads(output)
            return {}
        except Exception as e:
            print(f"Exception loading SpoonOS env: {e}")
            return {}

    def get_contract_address(self, contract_name: str) -> Optional[str]:
        """Retrieve a contract address by name."""
        return self.addresses.get(contract_name)

    def get_abi(self, contract_name: str) -> Optional[List]:
        """Retrieve a contract ABI by name."""
        return self.abis.get(contract_name)

    def post_job(self, title: str, skills: List[str], budget_usd: float) -> Dict:
        """
        Post a new job to the marketplace.

        Args:
            title: Job title
            skills: List of required skills/tags
            budget_usd: Budget in USDC

        Returns:
            Job metadata dict (actual on-chain post would require signing)
        """
        job_metadata = {
            "title": title,
            "required_skills": skills,
            "budget_usd": budget_usd,
            "status": "open",
        }

        print(f"[SpoonOS] Posting job: {title}")
        print(f"  OrderBook address: {self.get_contract_address('orderBook')}")
        print(f"  Metadata: {job_metadata}")

        # In a real SpoonOS agent, this would:
        # 1. Encode the metadata
        # 2. Call OrderBook.postJob() via ethers.js or web3.py
        # 3. Return the transaction receipt

        return {"status": "pending_signature", "metadata": job_metadata}

    def list_active_jobs(self) -> Dict:
        """List active jobs from JobRegistry."""
        print("[SpoonOS] Listing active jobs")
        print(f"  JobRegistry address: {self.get_contract_address('jobRegistry')}")

        # In a real agent, this would query the chain or an indexer
        return {"jobs": [], "total": 0}

    def search_agents(self, skills: List[str]) -> Dict:
        """Search for agents with matching skills in AgentRegistry."""
        print(f"[SpoonOS] Searching for agents with skills: {skills}")
        print(f"  AgentRegistry address: {self.get_contract_address('agentRegistry')}")

        # In a real agent, this would query the chain or an indexer
        return {"agents": [], "total": 0}

    def get_agent_reputation(self, agent_address: str) -> Optional[float]:
        """Retrieve an agent's reputation score."""
        print(f"[SpoonOS] Fetching reputation for agent: {agent_address}")
        print(
            f"  ReputationToken address: {self.get_contract_address('reputationToken')}"
        )

        # In a real agent, this would call ReputationToken.getReputation(agent_address)
        return None

    def place_bid(self, job_id: str, bid_amount_usd: float) -> Dict:
        """Place a bid on a job."""
        print(f"[SpoonOS] Placing bid on job {job_id} for ${bid_amount_usd}")
        print(f"  OrderBook address: {self.get_contract_address('orderBook')}")

        # In a real agent, this would:
        # 1. Check USDC allowance
        # 2. Call OrderBook.placeBid(jobId) with bid amount
        # 3. Return transaction receipt

        return {"status": "pending_signature", "job_id": job_id, "amount": bid_amount_usd}

    def approve_delivery(self, job_id: str) -> Dict:
        """Approve delivery and release escrow payment."""
        print(f"[SpoonOS] Approving delivery for job {job_id}")
        print(f"  Escrow address: {self.get_contract_address('escrow')}")

        # In a real agent, this would call Escrow.releaseFunds(jobId, agentAddr)
        return {"status": "pending_signature", "job_id": job_id}

    def get_environment_info(self) -> Dict:
        """Return environment info (chain, contracts, ABIs)."""
        return {
            "mode": self.env_mode,
            "network": self.addresses.get("network", "unknown"),
            "chain_id": self.addresses.get("chainId", "unknown"),
            "contracts": {
                k: v for k, v in self.addresses.items() if k != "network" and k != "chainId"
            },
            "abi_names": list(self.abis.keys()),
        }


# Example usage (for testing locally)
if __name__ == "__main__":
    print("=== NeoxPrep SpoonOS Agent Example ===\n")

    # Initialize the agent
    agent = NeoxPrepSpoonAgent(env_mode="read_only")

    # Print environment info
    print("Environment Info:")
    info = agent.get_environment_info()
    print(json.dumps(info, indent=2))

    print("\n=== Example Operations ===\n")

    # Example: Post a job
    job = agent.post_job(
        title="Build a Data Pipeline",
        skills=["Python", "Data Engineering"],
        budget_usd=5000.0,
    )
    print(f"Job posted: {json.dumps(job, indent=2)}\n")

    # Example: Search for agents
    agents = agent.search_agents(skills=["Python", "Data Engineering"])
    print(f"Agents found: {json.dumps(agents, indent=2)}\n")

    # Example: List active jobs
    jobs = agent.list_active_jobs()
    print(f"Active jobs: {json.dumps(jobs, indent=2)}\n")

    print("=== Agent Ready for SpoonOS ===")
    print("Deploy this agent to SpoonOS cloud to enable marketplace automation.")
