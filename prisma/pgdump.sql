--
-- PostgreSQL database dump
--

\restrict peQ9IHfWaLlb81UZzY3DieF7psX0cfOZYVMPf6Q4mCY5GecclWmwTQDx9jOL9v0

-- Dumped from database version 16.11 (Homebrew)
-- Dumped by pg_dump version 16.11 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: Agent; Type: TABLE; Schema: public; Owner: swarmuser
--

CREATE TABLE public."Agent" (
    id integer NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    category text,
    "priceUsd" double precision DEFAULT 0 NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    tags text,
    network text DEFAULT 'sepolia'::text,
    image text,
    "ownerId" integer NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone NOT NULL
);


ALTER TABLE public."Agent" OWNER TO swarmuser;

--
-- Name: Agent_id_seq; Type: SEQUENCE; Schema: public; Owner: swarmuser
--

CREATE SEQUENCE public."Agent_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Agent_id_seq" OWNER TO swarmuser;

--
-- Name: Agent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: swarmuser
--

ALTER SEQUENCE public."Agent_id_seq" OWNED BY public."Agent".id;


--
-- Name: Order; Type: TABLE; Schema: public; Owner: swarmuser
--

CREATE TABLE public."Order" (
    id integer NOT NULL,
    "agentId" integer NOT NULL,
    "buyerId" integer,
    "txHash" text NOT NULL,
    "amountEth" double precision NOT NULL,
    network text NOT NULL,
    "walletAddress" text NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public."Order" OWNER TO swarmuser;

--
-- Name: Order_id_seq; Type: SEQUENCE; Schema: public; Owner: swarmuser
--

CREATE SEQUENCE public."Order_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Order_id_seq" OWNER TO swarmuser;

--
-- Name: Order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: swarmuser
--

ALTER SEQUENCE public."Order_id_seq" OWNED BY public."Order".id;


--
-- Name: User; Type: TABLE; Schema: public; Owner: swarmuser
--

CREATE TABLE public."User" (
    id integer NOT NULL,
    email text NOT NULL,
    "passwordHash" text NOT NULL,
    name text,
    "walletAddress" text,
    role text DEFAULT 'user'::text NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public."User" OWNER TO swarmuser;

--
-- Name: User_id_seq; Type: SEQUENCE; Schema: public; Owner: swarmuser
--

CREATE SEQUENCE public."User_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."User_id_seq" OWNER TO swarmuser;

--
-- Name: User_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: swarmuser
--

ALTER SEQUENCE public."User_id_seq" OWNED BY public."User".id;


--
-- Name: _prisma_migrations; Type: TABLE; Schema: public; Owner: swarmuser
--

CREATE TABLE public._prisma_migrations (
    id character varying(36) NOT NULL,
    checksum character varying(64) NOT NULL,
    finished_at timestamp with time zone,
    migration_name character varying(255) NOT NULL,
    logs text,
    rolled_back_at timestamp with time zone,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_steps_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public._prisma_migrations OWNER TO swarmuser;

--
-- Name: Agent id; Type: DEFAULT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."Agent" ALTER COLUMN id SET DEFAULT nextval('public."Agent_id_seq"'::regclass);


--
-- Name: Order id; Type: DEFAULT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."Order" ALTER COLUMN id SET DEFAULT nextval('public."Order_id_seq"'::regclass);


--
-- Name: User id; Type: DEFAULT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."User" ALTER COLUMN id SET DEFAULT nextval('public."User_id_seq"'::regclass);


--
-- Data for Name: Agent; Type: TABLE DATA; Schema: public; Owner: swarmuser
--

COPY public."Agent" (id, title, description, category, "priceUsd", status, tags, network, image, "ownerId", "createdAt", "updatedAt") FROM stdin;
1	Lead Gen Agent	Automates outreach and captures qualified leads across email and LinkedIn.	Sales	49	active	leadgen,outreach,crm	neox-testnet	\N	1	2025-12-06 11:44:47.427	2025-12-06 11:44:47.427
2	Support Copilot	Triage and respond to support tickets with human-in-the-loop approvals.	Support	29	active	support,helpdesk	neox-testnet	\N	1	2025-12-06 11:44:47.43	2025-12-06 11:44:47.43
3	 Test	ststststststtstststs	Automation	25	active	Reservation 	Neo X Testnet	\N	2	2025-12-06 12:01:54.453	2025-12-06 12:01:54.453
\.


--
-- Data for Name: Order; Type: TABLE DATA; Schema: public; Owner: swarmuser
--

COPY public."Order" (id, "agentId", "buyerId", "txHash", "amountEth", network, "walletAddress", "createdAt") FROM stdin;
\.


--
-- Data for Name: User; Type: TABLE DATA; Schema: public; Owner: swarmuser
--

COPY public."User" (id, email, "passwordHash", name, "walletAddress", role, "createdAt") FROM stdin;
1	demo@swarm.ai	$2a$10$7kQhqjkY.NCUm0D5mRnX5..6wW8ffH6sMp/qtNH9JFwbeE8dyCidu	Demo User	0x000000000000000000000000000000000000dEaD	user	2025-12-06 11:44:47.424
2	kolya1maklakov@gmail.com	$2a$10$1rxPAm8yOvzLecrf7.Luq.lUdwbr/4VkIcqwCJIRdAe9vvUuIn33S	Nick	0x3a93d233707c447aCE1f5F014B81Cdaf53775273	user	2025-12-06 11:48:47.984
\.


--
-- Data for Name: _prisma_migrations; Type: TABLE DATA; Schema: public; Owner: swarmuser
--

COPY public._prisma_migrations (id, checksum, finished_at, migration_name, logs, rolled_back_at, started_at, applied_steps_count) FROM stdin;
df4a274e-9a19-4317-85e2-0b3d4717f212	ed15202521b8e6b1dfce57753dec7fc9ab2838fbad2d416836688d8c3c5ad656	2025-12-06 11:44:42.221139+00	20251206114442_init	\N	\N	2025-12-06 11:44:42.215107+00	1
\.


--
-- Name: Agent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: swarmuser
--

SELECT pg_catalog.setval('public."Agent_id_seq"', 3, true);


--
-- Name: Order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: swarmuser
--

SELECT pg_catalog.setval('public."Order_id_seq"', 1, false);


--
-- Name: User_id_seq; Type: SEQUENCE SET; Schema: public; Owner: swarmuser
--

SELECT pg_catalog.setval('public."User_id_seq"', 2, true);


--
-- Name: Agent Agent_pkey; Type: CONSTRAINT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."Agent"
    ADD CONSTRAINT "Agent_pkey" PRIMARY KEY (id);


--
-- Name: Order Order_pkey; Type: CONSTRAINT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."Order"
    ADD CONSTRAINT "Order_pkey" PRIMARY KEY (id);


--
-- Name: User User_pkey; Type: CONSTRAINT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."User"
    ADD CONSTRAINT "User_pkey" PRIMARY KEY (id);


--
-- Name: _prisma_migrations _prisma_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public._prisma_migrations
    ADD CONSTRAINT _prisma_migrations_pkey PRIMARY KEY (id);


--
-- Name: User_email_key; Type: INDEX; Schema: public; Owner: swarmuser
--

CREATE UNIQUE INDEX "User_email_key" ON public."User" USING btree (email);


--
-- Name: Agent Agent_ownerId_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."Agent"
    ADD CONSTRAINT "Agent_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES public."User"(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: Order Order_agentId_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."Order"
    ADD CONSTRAINT "Order_agentId_fkey" FOREIGN KEY ("agentId") REFERENCES public."Agent"(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: Order Order_buyerId_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swarmuser
--

ALTER TABLE ONLY public."Order"
    ADD CONSTRAINT "Order_buyerId_fkey" FOREIGN KEY ("buyerId") REFERENCES public."User"(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict peQ9IHfWaLlb81UZzY3DieF7psX0cfOZYVMPf6Q4mCY5GecclWmwTQDx9jOL9v0

