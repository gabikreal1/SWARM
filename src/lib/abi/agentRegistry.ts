export const agentRegistryAbi = [
  {
    type: "function",
    name: "registerAgent",
    stateMutability: "nonpayable",
    inputs: [
      { name: "name", type: "string" },
      { name: "metadataURI", type: "string" },
      { name: "capabilities", type: "string[]" },
    ],
    outputs: [],
  },
  {
    type: "function",
    name: "updateAgent",
    stateMutability: "nonpayable",
    inputs: [
      { name: "name", type: "string" },
      { name: "metadataURI", type: "string" },
      { name: "capabilities", type: "string[]" },
      { name: "status", type: "uint8" },
    ],
    outputs: [],
  },
  {
    type: "function",
    name: "getAgent",
    stateMutability: "view",
    inputs: [{ name: "wallet", type: "address" }],
    outputs: [
      {
        components: [
          { name: "name", type: "string" },
          { name: "metadataURI", type: "string" },
          { name: "capabilities", type: "string[]" },
          { name: "reputation", type: "uint256" },
          { name: "status", type: "uint8" },
          { name: "createdAt", type: "uint256" },
          { name: "updatedAt", type: "uint256" },
        ],
        name: "",
        type: "tuple",
      },
    ],
  },
] as const;

