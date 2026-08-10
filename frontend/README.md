# Passline — frontend

Static, dependency-free HTML/CSS/JS that talks directly to the deployed API
Gateway endpoint. No build step, no framework, no npm install.

## 1. Point it at your API

Edit `config.js`:
```js
window.APP_CONFIG = {
  API_BASE: "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev/",
};
```
Use the `ApiEndpoint` value from your `sam deploy` output (or
`aws cloudformation describe-stacks --stack-name event-ticketing-dev --query "Stacks[0].Outputs"`).
Keep the trailing slash.

## 2. Preview locally

Any static file server works — e.g.:
```bash
cd frontend
python -m http.server 8080
```
Open `http://localhost:8080`. If you see a "Not configured" status pill, `config.js` still has the placeholder URL.

## 3. Deploy on AWS Amplify Hosting, connected to GitHub

1. Push this repo to GitHub (frontend included) if you haven't already.
2. AWS Console → **Amplify** → **Create new app** → **Host web app** → choose **GitHub**, authorize, pick this repository and the `main` branch.
3. Amplify auto-detects `amplify.yml` at the repo root, which points it at the `frontend/` folder as the app root and serves it as-is — no build command needed. If Amplify's UI asks you to confirm build settings, the detected app root should read `frontend`.
4. Deploy. Amplify gives you a `https://<branch>.<app-id>.amplifyapp.com` URL — that's your live site.
5. Every push to `main` auto-redeploys the frontend (separate from the backend's own GitHub Actions pipeline, which deploys the API).

### CORS note

The API's `template.yaml` already sets `AllowOrigin: "'*'"` on API Gateway, so requests from your Amplify domain work without extra configuration. If you later lock CORS down to a specific origin for production, add your Amplify domain (`https://main.xxxxx.amplifyapp.com`) to the `AllowOrigin` list in `template.yaml` and redeploy the backend.

### Custom domain (optional)

Amplify Hosting → your app → **Domain management** → add a domain you own; Amplify handles the ACM certificate and DNS validation for you.
