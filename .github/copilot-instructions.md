This repository implements a small serverless bulk-email sender using Python, AWS SES, Lambda, API Gateway, and a simple Tkinter/web UI.

Quick orientation (big picture)
- Components:
  - `bulk_email_sender.py` — local Tkinter desktop GUI used for running campaigns locally with direct boto3 SES calls.
  - `web_ui.html` + `api_gateway_lambda.py` — browser UI and API Gateway Lambda proxy that exposes `/contacts` and `/campaign` endpoints (see `api_gateway_config.json`).
  - `lambda_email_sender.py` — Lambda backend that scans a DynamoDB table `EmailContacts`, sends via SES, and updates tracking fields.
  - Infrastructure helpers: `deploy_api_gateway.py`, `deploy_lambda.py`, `dynamodb_table_setup.py`, `create_iam_resources.py` and policy JSON files.

Key patterns and conventions (do not change without tests):
- Placeholder personalization uses double-curly markers: `{{first_name}}`, `{{last_name}}`, `{{email}}`, `{{company}}` — implemented in `personalize_content` in both `lambda_email_sender.py` and `bulk_email_sender.py`.
- DynamoDB table name is `EmailContacts` (hardcoded in Lambdas). Keep that name when editing infra or lambda code.
- SES region in Lambda code uses `us-gov-west-1` in `lambda_email_sender.py` and `api_gateway_lambda.py`. Verify region consistency if changing.
- API Gateway routes use resources `/contacts` and `/campaign` and expect/return JSON with keys shown in `README_WebUI.md` and `api_gateway_config.json`.

Developer workflows (commands & files to run)
- Install dependencies for local UI or scripts: `pip install -r requirements.txt` (desktop GUI) and `pip install -r requirements_lambda.txt` for Lambda packaging if needed.
- Create DynamoDB table (local deploy): `python dynamodb_table_setup.py` — this script creates `EmailContacts`.
- IAM and deployment helpers: `python create_iam_resources.py` to create roles/policies; update `iam_policies.json` and `ses_setup_policy.json` as needed.
- Deploy API & Lambda: update `YOUR_ACCOUNT_ID` in `deploy_api_gateway.py`, then `python deploy_lambda.py` and `python deploy_api_gateway.py` (scripts expect AWS CLI credentials or environment variables).
- Run desktop GUI: `python bulk_email_sender.py`; run Lambda locally with event-based tests by invoking handler functions or packaging/uploading.

Integration notes and gotchas
- The desktop GUI stores runtime AWS credentials in `config.json` (gitignored). Never commit credentials.
- API Gateway integration in `api_gateway_config.json` uses AWS Proxy (lambda proxy) and CORS headers are added in `api_gateway_lambda.py` — tests should include OPTIONS requests.
- Rate limiting is implemented client-side (sleep 1/send_rate). Production systems must use SES quotas and server-side throttling.
- DynamoDB numeric values appear as Decimal objects; handlers convert Decimal to int for JSON serialization (see `get_contacts`). Preserve that conversion when extending responses.

Edit guidance and examples
- To add a new field to contacts (`company_title`):
  1. Update `dynamodb_table_setup.py` (if schema-like defaults are used).
  2. Update `bulk_email_sender.py` UI (contacts columns and CSV headers).
  3. Update `lambda_email_sender.py` and `api_gateway_lambda.py` to persist and read the new attribute.

- Example: the API POST to `/contacts` expects body `{"contact": {"email":..., "first_name":...}}` (see `api_gateway_lambda.py` and `README_WebUI.md`). Mirror this shape in tests and UI code.

Files to inspect first for any change:
- `api_gateway_lambda.py`, `lambda_email_sender.py`, `bulk_email_sender.py`, `deploy_api_gateway.py`, `dynamodb_table_setup.py`, `web_ui.html`, `README_WebUI.md`.

Testing and validation pointers
- Unit tests are not included. Prefer small manual smoke tests:
  - Local GUI: run `python bulk_email_sender.py`, load `sample_contacts.csv`, preview email, and test SES connection with verified identities.
  - Lambda/API: use AWS SAM or call `lambda_email_sender.lambda_handler` with a minimal event `{"action": "get_contacts"}` to validate DynamoDB connectivity (requires AWS credentials).

If anything here is unclear or you need deeper coverage (tests, CI, or a change list), tell me which part to expand and I'll update this file.
