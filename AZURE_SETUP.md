# Azure OpenAI setup — QueryOpt AI

This project uses the Azure OpenAI deployment shown in your Foundry screenshot. The expected deployment name is `gpt-5-mini`.

## 1. Values you must supply

| Placeholder | File/location | What to enter | Where to get it |
|---|---|---|---|
| `https://your-resource-name.openai.azure.com` | `.env.example` → `AZURE_OPENAI_ENDPOINT` | The exact endpoint URL for your Azure OpenAI resource. Do not append `/openai/v1/`; the application adds that path automatically. | Azure Portal → Azure OpenAI resource `research-openai-903` → **Keys and Endpoint** / **Endpoints** → copy **Endpoint**. Confirm the displayed value rather than assuming the URL from the resource name. |
| `your_azure_openai_key_here` | `.env.example` → `AZURE_OPENAI_API_KEY` | Key 1 or Key 2 for that same resource. Treat it as a password. | Azure Portal → resource `research-openai-903` → **Keys and Endpoint** → copy **KEY 1** or **KEY 2**. Never put this in source code or share it. |
| `gpt-5-mini` | `.env.example` → `AZURE_OPENAI_DEPLOYMENT` | Already set to the deployment name visible in your screenshot. Keep it exactly as `gpt-5-mini` unless you rename the deployment in Foundry. | Foundry portal → **Model deployments** → **Name** column. Your screenshot shows `gpt-5-mini` and State `Succeeded`. |

The model version shown in Foundry (`2025-08-07`) is not a configuration placeholder and does not need to be entered. The app uses the deployment **name**. No separate `api-version` field is needed for the Azure OpenAI v1 endpoint.

## 2. Create your local `.env` file

From the project root in VS Code's terminal:

```bash
cp .env.example .env
```

Open `.env` and replace the endpoint and key placeholders with the exact values copied from Azure. Keep `AZURE_OPENAI_DEPLOYMENT=gpt-5-mini`. The `.env` file is excluded by `.gitignore`; do not commit it.

Example structure (the endpoint and key below are deliberately placeholders):

```env
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_API_KEY=your_azure_openai_key_here
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
```

Alternatively, after building the updated frontend, open the app's Azure OpenAI settings and enter the endpoint, key, and deployment there. **Test & Connect** checks the deployment and saves the values in `.env`.

## 3. Build and run

The Python server serves the compiled React app from `static/`. The ZIP contains the project's existing static build; rebuild it once to get the updated Azure settings dialog from `frontend/src/`.

```bash
# From the project root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

python app.py
```

Open `http://localhost:8000`. The database is created and seeded automatically on first launch.

## 4. Verify the Azure connection

1. Open the app's settings / AI connection dialog.
2. Confirm the endpoint, enter Key 1 or Key 2, and keep deployment name `gpt-5-mini`.
3. Select **Test & Connect**.
4. A successful message confirms the live Azure request. If it fails, check the endpoint, key, deployment name, quota, and whether the deployment is still in the `Succeeded` state.

## 5. Other placeholders

- In `frontend/src/components/AzureOpenAIModal.jsx`, the endpoint input's `placeholder` text is only a visual example (`https://your-resource-name.openai.azure.com`). It is not used as a configuration value. Enter the actual endpoint in the dialog.
- The API-key input's `placeholder` text (`Paste Key 1 or Key 2`) is a UI hint, not a value to edit in source code.
- The deployment input's `placeholder` (`gpt-5-mini`) matches your current deployment name.
- The `your-resource-name` / `your_azure_openai_key_here` strings in `.env.example` and this guide are the only values that must be replaced for manual `.env` configuration.

No Gemini API key is required by the updated Azure integration.

## 6. Troubleshooting: empty response from GPT-5 mini

The Azure connection test uses the Responses API. GPT-5 mini can spend output tokens on internal reasoning before it emits visible text. `max_output_tokens` includes both reasoning and visible output, so a very small budget (for example, 32 tokens) can produce an incomplete response with an empty `output_text`, even when Azure accepted the request. The current client uses `reasoning.effort=minimal`, explicitly requests a text response for the connection test, and allocates a larger output-token budget. SQL generation uses a larger budget for its structured JSON response.

After updating the project, stop the old server with `Ctrl+C` and start it again using `python app.py`. Then open Settings → Test & Connect. No Azure resource or deployment changes are required for this specific token-budget issue. If it still fails, copy the full error message shown by the app and check the terminal running `python app.py`; do not share your API key.
