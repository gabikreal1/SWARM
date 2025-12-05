export const orderBookAbi = [
  {
    type: "function",
    name: "postJob",
    stateMutability: "nonpayable",
    inputs: [
      { name: "description", type: "string" },
      { name: "metadataURI", type: "string" },
      { name: "tags", type: "string[]" },
      { name: "deadline", type: "uint64" },
    ],
    outputs: [{ name: "jobId", type: "uint256" }],
  },
  {
    type: "function",
    name: "getJob",
    stateMutability: "view",
    inputs: [{ name: "jobId", type: "uint256" }],
    outputs: [
      {
        components: [
          { name: "poster", type: "address" },
          { name: "status", type: "uint8" },
          { name: "acceptedBidId", type: "uint256" },
          { name: "deliveryProof", type: "bytes32" },
          { name: "hasDispute", type: "bool" },
        ],
        name: "job",
        type: "tuple",
      },
      {
        components: [
          { name: "id", type: "uint256" },
          { name: "jobId", type: "uint256" },
          { name: "bidder", type: "address" },
          { name: "price", type: "uint256" },
          { name: "deliveryTime", type: "uint64" },
          { name: "reputation", type: "uint256" },
          { name: "metadataURI", type: "string" },
          { name: "responseURI", type: "string" },
          { name: "accepted", type: "bool" },
          { name: "createdAt", type: "uint256" },
        ],
        name: "jobBids",
        type: "tuple[]",
      },
    ],
  },
] as const;

