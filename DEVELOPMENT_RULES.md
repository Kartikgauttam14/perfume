# Development Rules

Guiding principle: **the smallest, clearest codebase that does the job.**
Every rule below exists to reduce lines of code, reduce moving parts, and
reduce the effort needed to read, run, or deploy the project.

---

## 1. Prefer Libraries Over Custom Code

- Never hand-write something a well-maintained library already does
  (parsing, HTTP, retries, validation, CLI args, config loading, logging,
  chunking, embeddings, vector storage, etc.).
- Before writing a function, ask: *"Does `requests`, `pydantic`, `click`,
  `tenacity`, `langchain`, `pandas`, etc. already do this?"* If yes, use it.
- One well-known library beats 50 lines of bespoke code — it's also
  already tested, documented, and understood by anyone else reading the repo.
- Only write custom logic for the actual business problem — the thing
  that makes *this* project unique.

## 2. Object-Oriented, Not Over-Engineered

- Use classes to group state + behavior that belongs together (e.g. one
  class per pipeline stage: `Loader`, `Chunker`, `Embedder`, `Retriever`).
- One class = one responsibility. If a class needs "and" to describe it
  ("loads files **and** chunks them **and** talks to the API"), split it.
- Prefer composition over inheritance. Use inheritance only for genuine
  is-a relationships (e.g. `PDFLoader(BaseLoader)`), not to share
  unrelated utility code.
- No deep class hierarchies (max 1–2 levels). No design patterns unless
  they remove code, not add ceremony.
- Use `@dataclass` / `pydantic.BaseModel` for data containers instead of
  hand-rolled `__init__` boilerplate.

## 3. Compact & Readable Code

- Functions do one thing. If a function needs a comment to explain its
  middle section, split that section into its own function.
- Target: functions under ~30 lines, files under ~300 lines. If a file
  grows past that, it's doing too much — split it.
- No premature abstraction. Don't build a plugin system, config
  framework, or factory pattern for a single use case. Add abstraction
  only when a second real use case shows up.
- Prefer standard-library and built-in solutions (`pathlib`, `json`,
  `itertools`, list/dict comprehensions) over manual loops where they
  read more clearly.
- Flat is better than nested — avoid more than 2–3 levels of
  indentation; extract a function instead.

## 4. Minimal Dependencies, Minimal Surface Area

- Every new dependency must earn its place — prefer one library that
  covers several needs over several libraries that each cover one.
- No dead code, no unused imports, no commented-out blocks left in the
  repo — delete instead of hoarding "just in case."
- Config lives in one place (`.env` / `config.yaml` / `settings.py`),
  not scattered as magic numbers across files.
- Avoid clever/implicit code (metaclasses, monkey-patching, deep
  decorators) unless there's no simpler way — clarity beats cleverness.

## 5. Structure

```
project/
├── src/
│   ├── main.py          # entry point — thin, just wires things together
│   ├── <domain>.py       # one file per responsibility (loader, chunker, api)
├── tests/
├── requirements.txt      # or pyproject.toml
├── .env.example
├── Dockerfile             # if containerized
└── README.md
```

- `main.py` should read like a table of contents: create objects, call
  methods, done. No business logic in the entry point.
- Keep related code together; don't split one feature across five files
  "for organization" if three would do.

## 6. Error Handling & Logging

- Fail fast and loud — don't silently swallow exceptions.
- Use one shared logging setup, not `print()` scattered through the code.
- Wrap external calls (API, file I/O, DB) with clear error messages;
  let unexpected errors propagate rather than over-catching.

## 7. Testing

- Test behavior, not implementation — few, meaningful tests beat 100%
  coverage of trivial code.
- Every public function/class gets at least one test for its main path
  and one for its main failure case.
- Tests should run with a single command (`pytest`) and no manual setup.

## 8. Documentation

- Docstrings explain *why*, not *what* (the code already shows what).
- One README per project: what it does, how to run it, how to deploy
  it — nothing more. Skip auto-generated boilerplate docs no one reads.
- Type hints on every function signature — they double as
  documentation and catch bugs early.

## 9. Deployment — Keep It One Command

- The whole project should run with one command locally
  (`python main.py`, `docker compose up`, or similar) — no multi-step
  manual setup.
- Pin dependency versions (`requirements.txt` / lockfile) so "works on
  my machine" doesn't happen.
- Containerize with a single, small `Dockerfile` if deployment target
  needs it — avoid multi-stage complexity unless the image size truly
  requires it.
- No environment-specific code branches — use config/env vars instead
  of `if PRODUCTION:` scattered through the codebase.
- Prefer managed/serverless services over self-hosted infra when the
  scale doesn't need it — less to deploy, patch, and monitor.

## 10. Before Adding Anything, Ask

1. Does a library already solve this?
2. Can an existing class/function be reused instead of a new one?
3. Will this still make sense to someone reading it in 6 months with
   no context?
4. Does this make the project easier or harder to run/deploy?

If the answer to #4 is "harder," don't add it unless it's essential.

---

**Summary:** fewer files, fewer dependencies, fewer abstractions — but
correct, readable, and typed. Every line should justify its existence.
