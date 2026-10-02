# Government Scheme Assistant

An AI application that helps Indian students discover **government scholarships
and welfare schemes** they are actually eligible for.

It combines three things that are usually shown separately in tutorials:

1. **RAG** - every answer is written from a retrieved, curated knowledge base.
2. **Agentic AI (LangGraph)** - five specialised agents work in sequence.
3. **A deterministic rule engine** - eligibility is decided by exact rules, never
   by the language model.

> **Sample data notice.** The scheme records in this project are **illustrative
> sample data** used to demonstrate the pipeline. Income ceilings, benefit amounts
> and deadlines have **not** been verified against current official
> notifications. Always confirm on the official government portal before
> applying. See `knowledge_base/README.md`.

---



## Problem statement

Thousands of students miss out on scholarships and welfare schemes simply because
the information is scattered across dozens of government portals, in PDFs, in
different languages, with different eligibility rules.

The result is:

- Students do not know which schemes exist.
- They do not know which ones they qualify for.
- Deadlines are missed because nobody tracks them.
- Eligibility rules are confusing (category, income ceiling, age limit, course,
  disability, gender, state).

Generic chatbots do not solve this. They happily **invent** an income limit or a
deadline that sounds right, which is worse than saying nothing.

## Objectives

- Build a single place where a student can describe themselves in plain language
  and get a list of relevant schemes.
- Make every answer **traceable to a source record** (no invention of
  eligibility, benefits, deadlines or links).
- Use deterministic rules where correctness matters, and use the LLM only for
  explanation.
- Show the reasoning: which agent did what, which chunks were retrieved.
- Keep the LLM provider swappable and work even without an API key.

## Features

| Feature | Where |
|---|---|
| Single-page flow: questions → results → follow-up question | Home |
| Short "tell us about yourself" form (5 key fields, quick-pick chips, everything optional) | Step 1 |
| "You can apply / need a little more info / you miss one condition" with the exact failing rule | Step 2 |
| Question box with plain-English suggestions and saved-profile reuse | Step 3 |
| Manual browse / search / filter of the whole knowledge base | All schemes |
| Scheme cards: name, provider, who can apply, benefits, last date, official link | Everywhere |
| "Almost eligible" and "needs more info" buckets with the exact failing rule | Step 2 |
| Agent trace + retrieval scores, hidden behind a toggle | Step 2 / Step 3 |
| Automatic link / amount / date verification of the answer | Backend |
| Works with no API key (retrieval-only mode) | Backend |

The whole product is deliberately one page with three numbered steps. `All schemes`,
`Ask a question` and a shared scheme page exist so a user can bookmark or send a direct link.

## System architecture

```
┌──────────────────────────── React (Vite) frontend ────────────────────────────┐
│  Home (1 questions → 2 results → 3 ask)  │  All schemes  │  Ask  │  Scheme detail    │
│                     fetch() → src/api/client.js (single place)                │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │  JSON over HTTP (CORS enabled)
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│                          FastAPI backend (backend/)                           │
│  POST /chat   POST /recommend   GET /schemes   GET /schemes/{id}   GET /health  │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│                       LangGraph workflow (agents/)                            │
│                                                                               │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐   │
│  │  1. User   │──▶│  2. Scheme   │──▶│  3. Eligibility  │──▶│ 4. Recommend-│   │
│  │   Profile  │   │   Retrieval  │   │    Checking      │   │   ation      │   │
│  │   Agent    │   │   Agent      │   │    Agent         │   │   Agent      │   │
│  └────────────┘   └──────────────┘   └──────────────────┘   └──────┬───────┘   │
│        │                  │                   │                     │           │
│        │            ┌─────▼──────┐      ┌─────▼──────┐        ┌─────▼───────┐   │
│        │            │  RAG layer │      │   utils/   │        │   5. Response│  │
│        │            │  rag/      │      │ eligibility│        │    Agent     │  │
│        │            │ BM25 +     │      │ (rules, no │        │ + grounding  │  │
│        │            │ embeddings │      │    LLM)    │        │    check     │  │
│        │            └─────┬──────┘      └────────────┘        └──────┬───────┘   │
│        └──────────────────┴───────────────┬───────────────────────────┘           │
│                                           │                                       │
│                                 ┌─────────▼─────────┐   ┌──────────────────────┐  │
│                                 │  llm/ (provider    │   │ knowledge_base/      │  │
│                                 │  abstraction)      │   │ schemes.jsonl        │  │
│                                 │  grok / groq /     │   │ 15 sample schemes    │  │
│                                 │  openai / offline  │   └──────────────────────┘  │
│                                 └───────────────────┘                             │
└───────────────────────────────────────────────────────────────────────────────┘
```

Data flow for a single chat message:

```
message
  │
  ├─▶ 1. User Profile Agent       merge form profile + facts read from the text
  │                                (regex/rules, never the LLM)
  ├─▶ 2. Scheme Retrieval Agent   hybrid search (BM25 + embeddings) over 60 chunks
  │                                built from the 15 scheme records
  ├─▶ 3. Eligibility Checking     deterministic rules → eligible / not eligible /
  │      Agent                    needs more info  (+ the failing reason)
  ├─▶ 4. Recommendation Agent     rank by rule score × retrieval score, keep
  │                                near-misses
  └─▶ 5. Response Agent           build prompt from retrieved facts only → LLM
                                   → grounding check on links/amounts/dates
                                   → answer + citations + trace
```

## Technologies used

| Layer | Technology | Why |
|---|---|---|
| Frontend | React 18 + Vite | Fast dev server, simple build |
| Routing | react-router-dom | Home (one-page flow) / All schemes / Ask / Scheme detail |
| Styling | Plain CSS (custom properties) | No framework build step, easy to read |
| Backend | FastAPI + Uvicorn | Typed request/response models, auto OpenAPI docs at `/docs` |
| Validation | Pydantic v2 | One schema shared by API, agents and knowledge base |
| Agent orchestration | LangGraph | Explicit, inspectable multi-agent state machine |
| RAG | Custom hybrid retriever (BM25 + sentence-transformers) | No external vector DB needed, fully explainable |
| LLM | Grok (xAI) by default, Groq/OpenAI swappable | Requirement: `GROK_API_KEY` from env only |
| LLM fallback | Offline retrieval-only writer | App still works with zero API keys |
| Storage | JSONL file on disk | Human-editable, no DB setup |

## RAG implementation

Knowledge base → chunks → hybrid search → prompt → LLM → verification.

**1. Chunking** (`rag/chunking.py`)

One scheme becomes **4 chunks**: `overview`, `eligibility`, `benefits`,
`application`. Each chunk repeats the scheme name and provider so it is
self-contained. 15 schemes → **60 chunks**.

**2. Indexing** (`rag/retriever.py`)

- **BM25** (`k1=1.5`, `b=0.75`) implemented in pure Python - always available,
  no download, and excellent at matching scheme vocabulary.
- **Dense embeddings** via `sentence-transformers/all-MiniLM-L6-v2`, loaded in a
  **background thread** so startup is never blocked. If the model cannot be
  downloaded the app silently keeps using BM25.
- Scores are **min-max normalised and blended**:
  `score = 0.7 × bm25 + 0.3 × cosine` (`RAG_LEXICAL_WEIGHT`).
- At most **2 chunks per scheme** are kept, so one verbose scheme cannot
  dominate the prompt.

**3. Query construction**

The query is the user's message **plus** the profile
(`"Postgraduate MCA OBC Karnataka female 21 years old family income 2.0 lakh …"`).
A vague question like *"what can I apply for?"* still retrieves personalised
schemes. The user's words are repeated twice so their intent weighs more than the
profile fields.

**4. Prompting** (`rag/prompts.py`)

Retrieved records are rendered as explicit fact blocks:

```
<scheme id="SCH013">
Name: Karnataka Post Matric Scholarship for OBC Students
Provider: Department of Social Welfare, Government of Karnataka
Eligibility: OBC category student of Karnataka studying beyond Class 10 ...
Income limit: Family income up to Rs. 2.50 lakh per annum
Benefits: Reimbursement of tuition and non-refundable fees ...
Deadline: Sample deadline: 30-11-2026 (verify on the Karnataka portal)
Application link: https://ssp.postmatrichrms.karnataka.gov.in
Rule-engine result: Meets all 6 applicable criteria: age, family_income, ...
</scheme>
```

**5. Empty-context short circuit**

If nothing is retrieved, the LLM is **not called at all**. The app returns a
fixed "I do not have that information" reply listing what to do instead.

## Agentic AI / LangGraph implementation

`agents/graph.py` compiles a `StateGraph` with five nodes wired linearly:

```python
graph = StateGraph(AgentState)
graph.add_node("user_profile_agent",        profile_agent.run)
graph.add_node("scheme_retrieval_agent",    retrieval_agent.run)
graph.add_node("eligibility_checking_agent",eligibility_agent.run)
graph.add_node("recommendation_agent",      recommendation_agent.run)
graph.add_node("response_agent",            response_agent.run)

graph.set_entry_point("user_profile_agent")
graph.add_edge("user_profile_agent", "scheme_retrieval_agent")
...
graph.add_edge("response_agent", END)
```

| # | Agent | File | Does | LLM? |
|---|---|---|---|---|
| 1 | User Profile Agent | `agents/profile_agent.py` | Merges the form profile with facts read from the message (`21-year-old`, `₹2 lakh`, `Karnataka`, `pursuing MCA`) and normalises them | No |
| 2 | Scheme Retrieval Agent | `agents/retrieval_agent.py` | Hybrid search, de-duplicates chunks into candidate schemes, records retrieval scores | No |
| 3 | Eligibility Checking Agent | `agents/eligibility_agent.py` | Runs `utils/eligibility.py` and splits results into 3 buckets with reasons | No |
| 4 | Recommendation Agent | `agents/recommendation_agent.py` | Ranks by `0.6×rule_score + 0.3×retrieval_score + tag_bonus`, keeps near-misses | No |
| 5 | Response Agent | `agents/response_agent.py` | Builds the prompt, calls the LLM, runs the grounding check, returns citations | **Yes** |

**Why only the last agent uses an LLM** - this is the central design decision.
Eligibility is a rule problem; asking a language model to decide "is this person
eligible" is unreliable and unreproducible. So rules decide, and the LLM only
explains the result in natural language.

The state (`agents/state.py`) is a single `TypedDict` that flows through the
nodes, which is why the UI can show the full trace:

```
[User Profile Agent]      read 6 field(s) from the message (age, state, ...); still missing: category
[Scheme Retrieval Agent]  retrieved 12 chunk(s) covering 12 scheme(s) using hybrid (BM25 + embeddings)
[Eligibility Checking]    checked 12 scheme(s): 7 eligible, 5 not eligible, 0 need more details
[Recommendation Agent]    ranked 4 eligible scheme(s); 2 almost-eligible kept for reference
[Response Agent]          wrote the answer with grok (grok-4.6); grounded in 4 scheme(s)
```

**Fallback:** if `langgraph` is not installed, `run_workflow()` executes the same
five functions with a plain-python loop, so the project still runs.

## Anti-hallucination design

Three independent layers, which is the part worth highlighting:

1. **Strict prompts** - the system prompt states that only facts inside the
   `<scheme>` blocks may be used, that unknown fields must be reported as "not
   recorded", and that the model must say when the context is insufficient.
2. **Deterministic eligibility** - the LLM cannot change an eligibility verdict.
3. **Post-generation verification** (`utils/grounding.py`) - after generation the
   answer is re-checked against the retrieved text:
   - URLs not present in the knowledge base are **replaced** with
     `[link withheld: not present in the knowledge base]`.
   - Rupee amounts, "N lakh" values and dates are compared with the retrieved
     scheme text; anything unbacked raises a warning.
   - Warnings are returned to the UI as an amber banner (`grounded: false`).

Verified with a mock LLM that deliberately invented a link, a ₹5,00,000 amount
and a `31-12-2026` deadline - all three were caught:

```
WARNING | Response Agent: grounding warnings -> [
  'Removed link that is not in the knowledge base: https://fake-scholarship-portal.example.com/apply',
  'Rupee amount 5,00,000 is not present in the retrieved scheme text.',
  "Date '31-12-2026' is not present in the retrieved scheme text."]
```

## Project structure

```
scheme-assistant/
├── backend/                  FastAPI application
│   ├── main.py               app, CORS, startup warm-up
│   ├── config.py             all env-var settings
│   └── api/
│       ├── routes_chat.py        POST /chat
│       ├── routes_recommend.py   POST /recommend
│       ├── routes_schemes.py     GET  /schemes, /schemes/{id}, /filters, /stats
│       └── routes_meta.py        GET  /health, /meta
│
├── agents/                   LangGraph nodes (one file per agent)
│   ├── state.py              shared AgentState TypedDict
│   ├── profile_agent.py
│   ├── retrieval_agent.py
│   ├── eligibility_agent.py
│   ├── recommendation_agent.py
│   ├── response_agent.py
│   └── graph.py              StateGraph + python fallback runner
│
├── rag/                      Retrieval-Augmented Generation
│   ├── loader.py             read + validate schemes.jsonl
│   ├── chunking.py           scheme -> 4 retrievable chunks
│   ├── retriever.py          BM25 + embeddings hybrid search
│   └── prompts.py            prompts and context builders
│
├── llm/                      provider abstraction (swap in one file)
│   ├── base.py               BaseLLMClient interface
│   ├── openai_compatible.py  shared httpx client
│   ├── grok_client.py        Grok / xAI  <- default
│   ├── groq_client.py        Groq
│   ├── openai_client.py      OpenAI
│   ├── offline_client.py     no-API-key deterministic writer
│   └── factory.py            provider selection + safe fallback
│
├── models/                   Pydantic schemas
│   ├── profile.py            UserProfile
│   ├── scheme.py             Scheme, RetrievalChunk, RetrievalResult
│   └── api.py                request/response models
│
├── services/                 orchestration between HTTP and agents
│   ├── chat_service.py
│   ├── recommendation_service.py
│   └── scheme_service.py
│
├── utils/
│   ├── eligibility.py        deterministic rule engine (no LLM)
│   ├── grounding.py          post-generation fact verification
│   ├── normalize.py          "2 lakh" -> 200000, "obc" -> "OBC", ...
│   ├── profile_extractor.py  regex profile parsing from chat messages
│   ├── text_utils.py         tokenisation, synonyms, stop words
│   └── logging_utils.py
│
├── knowledge_base/
│   ├── schemes.jsonl         15 sample schemes
│   └── README.md             format + how to verify real data
│
├── frontend/                 React + Vite
│   ├── src/
│   │   ├── api/client.js     single place for the API base URL
│   │   ├── context/ProfileContext.jsx
│   │   ├── components/       Navbar, SchemeCard, TracePanel, Footer, Feedback, ProfileForm, AskBox
│   │   ├── pages/            Find (one-page flow), Browse, Chat, SchemeDetail, NotFound
│   │   ├── App.jsx           routes + metadata
│   │   └── styles.css
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Service banner + endpoint list |
| `GET` | `/health` | Status, LLM provider, retrieval mode, scheme count |
| `GET` | `/meta` | Everything the frontend needs on boot (filters, agents, disclaimer) |
| `GET` | `/schemes` | Browse/search/filter. Query params: `q`, `state`, `category`, `gender`, `education_level`, `provider`, `scheme_type`, `data_status`, `limit` |
| `GET` | `/schemes/filters` | Option lists for the filter dropdowns |
| `GET` | `/schemes/stats` | Knowledge-base statistics |
| `GET` | `/schemes/{id}` | One scheme (`404` if unknown) |
| `POST` | `/recommend` | Profile-driven recommendations |
| `POST` | `/chat` | Ask the assistant a question |

Interactive documentation: <http://127.0.0.1:8000/docs>

<details>
<summary>Example: <code>POST /chat</code></summary>

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am a 21-year-old student from Karnataka pursuing MCA. My family income is Rs 2 lakh per year. What scholarships am I eligible for?",
    "profile": {},
    "history": [],
    "top_n": 5
  }'
```

```jsonc
{
  "answer": "Based on your profile, ...",
  "matched_schemes": [ { "scheme_id": "SCH013", "name": "Karnataka Post Matric Scholarship for OBC Students", "...": "..." } ],
  "citations": ["SCH013 - Karnataka Post Matric Scholarship for OBC Students (Department of Social Welfare, Government of Karnataka)"],
  "profile_used": { "age": 21, "state": "Karnataka", "education_level": "Postgraduate", "course": "MCA", "family_income": 200000 },
  "missing_profile_fields": ["category"],
  "trace": [ { "agent": "User Profile Agent", "summary": "read 6 field(s) from the message ..." } ],
  "llm_provider": "grok",
  "llm_used": true,
  "grounded": true,
  "grounding_warnings": [],
  "disclaimer": "Demo/sample dataset ..."
}
```
</details>

<details>
<summary>Example: <code>POST /recommend</code></summary>

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "profile": {
      "age": 21, "gender": "Female", "state": "Karnataka", "category": "OBC",
      "family_income": 200000, "education_level": "Postgraduate",
      "course": "MCA", "student_status": "Full-time", "disability_status": "No"
    },
    "top_n": 6,
    "include_near_misses": true
  }'
```

Response buckets: `eligible`, `needs_more_info` (a mandatory rule could not be
verified), `near_misses` (exactly one criterion failed), plus the per-criterion
`checks` and `match_highlights` used by the UI.
</details>

## Installation

**Prerequisites:** Python 3.10+ and Node.js 18+.

### 1. Backend

```bash
cd scheme-assistant

# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment file

```bash
cp .env.example .env        # Windows PowerShell: copy .env.example .env
```

Edit `.env` and put your key in:

```env
GROK_API_KEY=your_key_here
```

> **No key yet?** Skip this. The app starts in *retrieval-only mode*: it answers
> from the knowledge base using a deterministic writer, and the UI shows a
> `RAG mode` badge instead of the provider name.

### 3. Frontend

```bash
cd frontend
npm install
```

## Running the application

Two terminals, from the project root.

**Terminal 1 - backend**

```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - frontend**

```bash
cd frontend
npm run dev
```

Open **<http://localhost:5173>**.

At startup the backend prints its configuration:

```
Government Scheme Assistant v1.0.0 starting
Knowledge base : ...\knowledge_base\schemes.jsonl (15 schemes)
Retrieval      : hybrid (BM25 + embeddings)
LLM provider   : grok (model=grok-4.6)
Agent graph ready (runtime=langgraph)
```

### Production build (optional)

```bash
cd frontend
npm run build        # outputs frontend/dist
npm run preview      # serves it on http://localhost:4173
```

`CORS_ORIGINS` in `.env` already allows ports 5173 and 4173.

## Environment variables

All settings live in `.env` (see `.env.example`). The important ones:

| Variable | Default | Meaning |
|---|---|---|
| `GROK_API_KEY` | – | xAI/Grok key. **The only required key, and optional** |
| `GROK_MODEL` | `grok-4.6` | Grok model id |
| `LLM_PROVIDER` | `auto` | `auto` \| `grok` \| `groq` \| `openai` \| `offline` |
| `GROQ_API_KEY` / `GROQ_MODEL` | – | Optional free-tier alternative |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | – | Optional: shows provider swapping |
| `LLM_TEMPERATURE` | `0.1` | Low on purpose - we want factual text |
| `LLM_MAX_TOKENS` | `900` | Max response length |
| `KNOWLEDGE_BASE_FILE` | `schemes.jsonl` | Which file to load |
| `RAG_TOP_K` | `6` | Chunks returned to the LLM |
| `RAG_LEXICAL_WEIGHT` | `0.7` | `1.0` = BM25 only, `0.0` = embeddings only |
| `EMBEDDING_ENABLED` | `true` | `false` skips the sentence-transformers download |
| `CORS_ORIGINS` | localhost:5173,4173 | Allowed frontend origins |
| `LOG_LEVEL` | `INFO` | Python log level |

**Swapping the LLM provider** is one line in `.env` (e.g. `LLM_PROVIDER=groq`
plus a `GROQ_API_KEY`). To add a brand-new provider, subclass
`llm/base.py:BaseLLMClient` and register it in `llm/factory.py` - no other file
changes.

## Example user queries

Try these in step 3 of the home page (or the **Ask a question** page):

1. `I am a 21-year-old student from Karnataka pursuing MCA. My family income is ₹2 lakh per year. What scholarships am I eligible for?`
2. `Are there any scholarships for postgraduate students?`
3. `I am a girl studying B.Tech in Tamil Nadu with a family income of 3 lakh. Any scholarship for me?`
4. `I am a differently abled student. What schemes support me?`
5. `I am an OBC student in class 11 in Kerala with family income 2 lakh per year.`
6. `What is the deadline for the Karnataka post matric scholarship?`
7. `I am an SC student studying MA history in Kerala with income 1.8 lakh.`
8. `Do you have any scheme for a PhD student from an OBC category family?`

Expected behaviour worth demonstrating:

- Query 1 → the assistant extracts age/state/income/course, checks rules and
  reports `category` as still missing instead of guessing it.
- Query 2 → answers purely from retrieval, with no eligibility claim, because
  there is no profile yet.
- Query 8 → `SCH011` (UGC fellowship for OBC, MPhil/PhD) is returned.
- Any nonsense question (*"Do you have schemes for buying a Mars rover?"*) → the
  honest *"I could not find a matching scheme in the knowledge base"* reply.

## Testing

```bash
# 1. Backend health
curl http://127.0.0.1:8000/health

# 2. Search
curl "http://127.0.0.1:8000/schemes?q=girls%20engineering"
curl "http://127.0.0.1:8000/schemes?state=Karnataka&category=OBC"

# 3. One scheme, and the 404 path
curl http://127.0.0.1:8000/schemes/SCH004
curl http://127.0.0.1:8000/schemes/NOPE      # -> 404

# 4. Chat (see the agent trace + citations)
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" \
  -d '{"message":"I am a 19-year-old OBC girl from Kerala studying BSc, family income 1.5 lakh. What can I apply for?"}'

# 5. Recommend
curl -X POST http://127.0.0.1:8000/recommend -H "Content-Type: application/json" \
  -d '{"profile":{"age":19,"gender":"Female","state":"Kerala","category":"OBC","family_income":150000,"education_level":"Undergraduate","course":"BSc"}}'
```

Offline unit checks (no server needed):

```bash
python -m utils.eligibility     # prints two eligibility check results
python -m utils.grounding       # exercises the fact checker
```



## Future enhancements

**Data**
- Scrape and verify real scheme data from official portals with a review queue,
  flipping `data_status` to `officially-published` after human review.
- Deadline reminders (email/WhatsApp) and a calendar export.
- Multilingual support (Hindi, Kannada, Tamil) including scheme documents.

**RAG / AI**
- Move from BM25+embeddings to a proper vector store (ChromaDB/pgvector) with
  incremental updates.
- Query rewriting, HyDE, and re-ranking (cross-encoder) for better recall.
- Compare several schemes side by side ("which gives me more money?").
- A second LLM pass that proposes *questions the user should ask* next.

**Product**
- Bookmarks and an application tracker (applied / rejected / pending).
- Document upload: the assistant reads a student's marksheet or income
  certificate to fill the profile automatically.
- SSO/login and a saved profile.
- Multilingual voice input.

**Engineering**
- Unit + integration tests with pytest and a mocked LLM (CI).
- Docker Compose for one-command startup.
- Caching layer (Redis) for repeated questions.
- Observability: token/latency logging, per-stage tracing, evaluation set of
  questions with expected scheme ids.
