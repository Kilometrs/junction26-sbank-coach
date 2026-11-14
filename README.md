# junction26-sbank-coach

Junction 2026 · S-Bank "Personal Economic Trainer" challenge.

A finance coach that understands **where you are in life** (student, moving out, new baby, lost job) and coaches you accordingly: first a safety net of 3–6 months of spending, then saving for goals.

## How it works
- **Engine (plain Python):** sorts spending into S-Bank's three categories (mandatory regular, mandatory irregular, everyday spending that slips away), finds recurring bills, computes the safety net and safe-to-spend, and runs what-ifs. All numbers come from here.
- **Coach (LLM):** understands the question, calls the engine and explains the answer in plain language. It never does the maths itself.
- **Life stage:** inferred from transactions, always confirmed by the user, opt-in.
- **UI:** phone-width page with cards and a chat, styled after S-mobiili.

## Data
Uses S-Bank's synthetic dataset, which is not included in this repo. Clone `hackjunction/Junction-2026-S-pankki` next to this repo and set `SBANK_DATA_DIR` in `.env` (see `.env.example`).

## Run
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                  # then add your API key
.venv/bin/python prep.py              # once: splits the dataset into data/tx/<customer>.csv.gz
.venv/bin/python engine.py CUST00152  # numbers only, no AI
.venv/bin/python coach.py CUST00152   # chat in the terminal
.venv/bin/uvicorn app:app --reload    # API + debug page on http://localhost:8000
```

## Dev container
`.devcontainer/` sets up everything: Python 3.14 with the API's packages in `.venv`, and Node 22 with the phone app's packages. Open the folder in VS Code and choose **Reopen in Container**, or use the CLI:
```bash
npx @devcontainers/cli up --workspace-folder .
```
- Inside the container, `.venv` and `mobile/node_modules` are Docker volumes. They don't touch the host's copies.
- `data/` and `.env` come from the project folder, so prepare the data and add your key as described above.
- Ports 8000 (API) and 8081 (Expo) are published on all of the host's network interfaces. Run the servers with `--host 0.0.0.0`.
- For Expo Go on a phone, set `REACT_NATIVE_PACKAGER_HOSTNAME=<laptop LAN IP>` and `EXPO_PUBLIC_API_URL=http://<laptop LAN IP>:8000` before `npx expo start`.

## Phone UI (React Native, `mobile/`)
Expo SDK 58 app built from the Claude Design mockup "Personal Economic Trainer – chatbot mockup": the coach chat with charts drawn inside its replies, and "Your money profile" (life-stage check, what the coach knows, privacy).
```bash
cd mobile && npm install
npx expo start --web                  # browser, talks to http://localhost:8000
npx expo start                        # Expo Go on a phone: see below
```
Start the API with `--host 0.0.0.0`. A real phone needs `EXPO_PUBLIC_API_URL=http://<laptop LAN IP>:8000 npx expo start`; the Android emulator uses `10.0.2.2` automatically.
No Node on the machine? `.claude/launch.json` runs Expo inside the `node:22` Docker image.

## API (for the UI)
| Endpoint | Returns |
|---|---|
| `GET /customers` | Demo customers: `[{id, label}]` |
| `GET /life-stages` | Life stages with label and safety-net target |
| `GET /profile/{id}?life_stage=` | Numbers for the cards: buckets, safety net, safe-to-spend, written profile |
| `POST /chat` | Body `{customer_id, messages, life_stage}`. Returns `{reply, cards, charts, options, life_stage}`. `cards` are the raw engine results behind the reply (`{tool, args, result}`). `charts` are the charts the coach drew, by id; the reply has a `[[chart:<id>]]` line where each one goes. `options` are 2–4 answers to the question the reply ends with (the coach sets them with its `ask_with_options` tool, for example "Yes, I'm a student" / "No, something else"); the app shows them as buttons, and tapping one sends it as the user's message. Empty when there is no such question. Send `life_stage` back on the next call, and strip the markers from the history you send (only the last 10 messages reach the model). A reply that is not a normal answer also has `error`: `llm_unavailable` when the language model fails, or `bad_request`, `too_long`, `rate_limited` or `daily_limit` when a demo limit refuses the message (see below); `reply` then holds the text to show. `saving_offer` is `{amount, purpose}` when the answer was about putting money aside (the app shows a simulated S-mobiili button), otherwise `null`. |

### Charts
The coach draws with five chart tools (`charts.py`): `bar_chart`, `line_chart`, `progress`, `before_after` and `key_figures`. It picks the type, writes the title and labels in the user's language, and fills in the values. The backend accepts a chart only if every number in it is one the engine returned while answering this message (or is in the customer's profile); numbers in titles and labels may also come from the tool arguments, like the 20 in "Restaurants −20%". Anything else is sent back to the model as an error, so a chart can never show a made-up or recalculated number. The app (`mobile/src/components/Visuals.tsx`) only formats and draws.

### Demo limits
`/chat` and `/profile` only serve the six demo customers. `/chat` also refuses, without calling the language model:
- more than 10 messages a minute from one visitor (`CHAT_PER_MINUTE`)
- more than 1,500 messages a day in total (`CHAT_DAILY_LIMIT`)
- a message longer than 500 characters (`CHAT_MAX_MESSAGE`)

Each model call is capped at 1,500 output tokens (`LLM_MAX_TOKENS`). The counts are kept in memory, so they reset when the server restarts and are per instance.

## Hosted demo (one container)
The `Dockerfile` builds one image with the API, the phone app as a website at `/` (the debug page and FastAPI's `/docs` are switched off there) and the data of the six demo customers. That data is `demo-data/` (1.4 MB), made by `python prep.py --demo` and committed only on the `prod-demo` branch.
```bash
git checkout prod-demo
docker build -t sbank-coach .
docker run -p 8080:8080 --env-file .env sbank-coach     # http://localhost:8080
```
The key is not in the image: pass it when the container starts. On Google Cloud Run (not tried yet):
```bash
gcloud run deploy sbank-coach --source . --region europe-north1 --allow-unauthenticated \
  --min-instances 0 --max-instances 1 --memory 512Mi \
  --set-env-vars CHAT_PROXY_HOPS=1,LLM_BASE_URL=https://openrouter.ai/api/v1,LLM_MODEL=anthropic/claude-haiku-5.5 \
  --set-secrets LLM_API_KEY=sbank-llm-key:latest
```
- `--max-instances 1` keeps the message limits meaningful, because each instance counts on its own.
- `CHAT_PROXY_HOPS=1` tells the limiter that one proxy (Google's) adds the visitor's address. Leave it at 0 when visitors connect directly.
- `sbank-llm-key` is a Secret Manager secret holding the API key.

## Demo customers
| Customer | Who | "Can I afford a €600 laptop?" |
|---|---|---|
| `CUST00152` | 21, income ~€1,500, half a month of safety net | wait |
| `CUST00001` | 63, stable, 2.8 months of safety net | yes, but it dips into the safety net |
| `CUST00007` | 49, stable, 10 months of safety net | yes |
| `CUST05014` | 23, irregular income, 0.4 months of safety net | wait |
| `CUST00983` | 48, started paying for housing a month ago, 5.4 months of safety net | yes |

## License
MIT, see [LICENSE](LICENSE).
