# Deploying Ruvia

Order matters a little: database first, then the API, then the app, then point them at each other.

| Piece | Service | Cost to start |
| --- | --- | --- |
| Database | Neon | Free tier |
| API | Render web service | Free tier (sleeps when idle) |
| App | Vercel | Free for personal use |
| Email codes | SendGrid | Trial, then a paid plan. See step 3 |
| Reminders | GitHub Actions (free) or a Render cron job (paid) | Free or a small monthly charge |
| Models | OpenAI, Gemini, Anthropic | Pay as you go. The app runs without them |

Prices and plans change, so check each site before you rely on a free tier.

---

## 0. Push the code to GitHub

Unzip, then from the `ruvia` folder:

```bash
git init
git add .
git commit -m "Ruvia"
git branch -M main
git remote add origin https://github.com/AshraySikka/ruvia.git
git push -u origin main
```

The `.gitignore` already keeps `.env` files, `node_modules` and the local database out of the repo.

## 1. Make your secret keys

Run these on your computer inside `backend` (after `pip install -r requirements.txt`). Keep the output somewhere safe, like a password manager.

```bash
# Encryption key for check-in text. If you lose this, encrypted entries cannot be read. Never change it after launch.
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Push notification keys
python manage.py generate_vapid

# A random secret for the reminder scheduler
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 2. Neon (database)

1. Sign in at neon.tech and create a project called `ruvia`. Pick a region close to where you will run Render (for example AWS US East if you pick Render's Ohio region).
2. Open **Connect**. Leave **Connection pooling** off and copy the connection string. It looks like:
   `postgresql://user:password@ep-something.us-east-2.aws.neon.tech/neondb?sslmode=require`
3. Keep `?sslmode=require` at the end. This is your `DATABASE_URL`.

Tables are created automatically when Render builds the API.

## 3. SendGrid (email codes)

SendGrid sends the 6 digit codes for sign up, sign in and password reset. It no longer has a permanent free plan: new accounts get a trial, then need a paid plan. If you would rather not pay, the email code is the only part that uses it, and the code in `backend/accounts/emails.py` is short enough to swap for another provider later.

1. Create an account at sendgrid.com.
2. Go to **Settings > Sender Authentication**. Either verify a single sender (quickest, use an email you own) or authenticate your domain (better delivery, needs DNS access, for example on ashraysikka.com).
3. Go to **Settings > API Keys > Create API Key**. Choose **Restricted Access**, turn on **Mail Send** only, and copy the key. You only see it once.
4. You now have `SENDGRID_API_KEY`, and `SENDGRID_FROM_EMAIL` is the sender you verified.

Until this is set, codes are written to the Render logs instead of emailed, which is handy for testing.

## 4. Render (API)

### Option A: Blueprint (fastest)

1. In Render, click **New > Blueprint** and pick your GitHub repo. Render reads `render.yaml`.
2. It creates an environment group called `ruvia-shared` and asks for the values marked secret. Fill them in using the table below.
3. The blueprint also includes a paid cron job. If you want to stay free, delete the `cron` block from `render.yaml` before you create the blueprint, and use the GitHub schedule in step 6.

### Option B: by hand

1. **New > Web Service**, connect the repo.
2. **Root Directory:** `backend`
3. **Runtime:** Python
4. **Build Command:** `./build.sh`
5. **Start Command:** `gunicorn config.wsgi:application --workers 2 --timeout 90`
6. **Health Check Path:** `/health/`
7. Add the environment variables below, then **Create Web Service**.

### Environment variables

| Key | Value |
| --- | --- |
| `DEBUG` | `false` |
| `PYTHON_VERSION` | `3.12.7` |
| `SECRET_KEY` | A long random string (Render can generate one) |
| `DATABASE_URL` | Your Neon connection string |
| `FIELD_ENCRYPTION_KEY` | The Fernet key from step 1 |
| `FRONTEND_URL` | Your Vercel URL, filled in after step 5. Use `https://placeholder.vercel.app` for now |
| `SENDGRID_API_KEY` | From step 3 |
| `SENDGRID_FROM_EMAIL` | Your verified sender |
| `OPENAI_API_KEY` | From platform.openai.com |
| `GEMINI_API_KEY` | From aistudio.google.com |
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `VAPID_PUBLIC_KEY` | From step 1 |
| `VAPID_PRIVATE_KEY` | From step 1 |
| `VAPID_SUBJECT` | `mailto:` plus your email, like `mailto:ashray@example.com` |
| `CRON_SECRET` | The random secret from step 1 |
| `SEED_DEMO` | `true` to create Jane and Joe once. `refresh` rebuilds them on every deploy so their dates stay current |
| `DEMO_PASSWORD` | `RuviaDemo2026!` or anything you like |
| `DJANGO_SUPERUSER_EMAIL` | Optional, your email, for the admin site |
| `DJANGO_SUPERUSER_PASSWORD` | Optional, a strong password |

Optional model settings, if you want to pick versions yourself: `OPENAI_MODEL` (default `gpt-4.1-mini`), `OPENAI_TRANSCRIBE_MODEL` (default `whisper-1`), `GEMINI_MODEL` (default `gemini-2.5-flash`), `ANTHROPIC_MODEL` (default `claude-haiku-5-5`). Model names change often, so check each provider's current list. If one name is wrong, Ruvia moves to the next provider and logs the error.

You can leave any model key empty. With no keys at all, the app still runs on keyword rules and templates. Voice needs the OpenAI key.

When the deploy finishes, open `https://YOUR-SERVICE.onrender.com/health/`. You should see `{"ok": true, "app": "ruvia"}`.

The admin site is at `/admin/` if you set the superuser variables.

**About the free plan:** the API goes to sleep after about 15 minutes without traffic, and the first request after that takes up to a minute. The reminder schedule in step 6 wakes it regularly, which helps.

## 5. Vercel (app)

1. In Vercel, **Add New > Project** and import the repo.
2. **Root Directory:** `frontend`. Vercel detects Vite on its own.
3. **Environment Variables:**
   - `VITE_API_URL` = your Render URL, like `https://ruvia-api.onrender.com` (no slash at the end)
   - `VITE_DEMO_PASSWORD` = the same demo password, if you want the "Try the demo" buttons on the welcome screen. Leave it out to hide them.
4. **Deploy.** `vercel.json` already handles page routing and the service worker headers.

## 6. Connect them

1. Back in Render, set `FRONTEND_URL` to your Vercel URL, like `https://ruvia.vercel.app`. If you add a custom domain later, set it to that instead. For more than one, also set `CORS_ALLOWED_ORIGINS` as a comma separated list.
2. Save. Render redeploys.

## 7. Reminders

Something needs to call the scheduler every few minutes. It plans check-ins, water nudges, follow-ups, period reminders and the weekly summary, then sends what is due. Running it extra times is safe.

**Free: GitHub Actions**

1. In your GitHub repo, go to **Settings > Secrets and variables > Actions**.
2. Add `RUVIA_API_URL` (your Render URL) and `CRON_SECRET` (same value as on Render).
3. Go to **Actions**, open **Ruvia reminders**, and click **Run workflow** once to test. After that it runs every 15 minutes. GitHub sometimes runs scheduled jobs a few minutes late, which is fine here.

**Paid: Render cron job**

If you kept the `cron` block in `render.yaml`, it runs `python manage.py run_scheduler` every 10 minutes using the same environment group. Do not run both options, though nothing breaks if you do.

## 8. Try it

1. Open your Vercel URL and tap **Try the demo as Jane**.
2. On a phone, install it:
   - **iPhone:** open in Safari, tap **Share > Add to Home Screen**, then open Ruvia from the home screen. Push reminders on iPhone only work from the installed app.
   - **Android:** Chrome shows an install prompt, or use the menu and **Install app**.
3. Go to **Me > Reminders > Turn on reminders**, then **Send a test reminder**.
4. Create your real account with your own email. The code arrives from SendGrid.
5. Invite Grusha from **Care > Invite someone**.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| The app says it cannot reach the server, or the browser console shows a CORS error | `FRONTEND_URL` on Render must exactly match the Vercel address, with `https://` and no slash at the end |
| First load is slow | The free Render API was asleep. Give it up to a minute |
| No email code | Check the sender is verified in SendGrid and the API key has Mail Send. Until then the code is in the Render logs |
| Replies sound plain and the chat says it is using built-in replies | No model key is set, or every provider failed. Render logs show which one and why |
| Voice says it is not set up | `OPENAI_API_KEY` is missing |
| No push on iPhone | Install to the home screen first, then turn reminders on from inside the installed app |
| "Push is not set up on the server yet" | `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` are missing on Render |
| Demo data looks old | Set `SEED_DEMO=refresh` and redeploy. Demo dates are based on the day they were created |
| Build fails on Python version | Set `PYTHON_VERSION` to `3.12.7` |

## Local development

See the README. Short version: `python manage.py runserver` in `backend` and `npm run dev` in `frontend`, with `VITE_API_URL=http://localhost:8000`.
