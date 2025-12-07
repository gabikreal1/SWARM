-- CreateTable
CREATE TABLE "CallSummary" (
    "id" SERIAL NOT NULL,
    "conversationId" TEXT,
    "callSid" TEXT,
    "status" TEXT,
    "summary" TEXT,
    "toNumber" TEXT,
    "jobId" TEXT,
    "neofsUri" TEXT,
    "payload" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CallSummary_pkey" PRIMARY KEY ("id")
);
