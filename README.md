# Ruvia

A small daily health diary for you and the people you love.

## Why this exists

Ruvia started with one person: my wife, Grusha.

I wanted something that would ask her how she was doing, remember what helped the last time a headache or acidity showed up, and quietly let me know when she was having a rough day without making her explain it. Nothing I tried did all of that, so I built it for us.

The name comes from her too. Ruvia grew out of Grusha's name, softened into something that sounds like a warm, small place to check in. Everything in the app, from the colours to the way it talks, is meant to feel like that.

## What it does

**Checking in**
- Type a sentence or tap the mic and talk. You see the transcript before anything saves.
- Ruvia picks out short tags for your calendar, like Acidity or Headache, and you can edit them.
- Rate your body and mind out of 10, or let Ruvia estimate from what you logged. Every score is labelled as self-rated or estimated, and the app explains exactly how scores are worked out.
- A Rough day button for days you do not want to explain anything.

**When something hurts**
- Home remedies first, then over the counter options like Pepcid or Tylenol.
- Before suggesting anything, Ruvia checks your history for what worked last time and puts it first.
- Your medicines and allergies are checked in code against every over the counter option. Clashes are removed or flagged with the reason.
- About an hour later it asks if you feel better, the same, or worse, and remembers what you tried.
- It never gives doses and always reminds you to ask your doctor or pharmacist.

**Safety**
- Fixed rules run before anything else. Signs of an emergency (a sudden severe headache, chest pain, trouble breathing, stroke signs and more) get a fixed reply pointing to 911 or Health811, with no home remedies.
- Any mention of self-harm gets a fixed, kind reply with the 9-8-8 Suicide Crisis Helpline, and nothing else.

**Mood**
- Curated suggestions for how you feel, including the famous three: feel like everyone hates you, sleep. Feel like you hate everyone, eat. Feel like you hate yourself, shower.
- Tap what helped and it moves to the top next time.

**Water, cycle and calendar**
- Water tracker with a daily goal and reminders that only fire when you are behind for the time of day.
- Cycle tracking with predictions, tips for each phase, a heads up two days before, and a "did it start today?" question on the expected day.
- A heat map calendar: plum for hard days, green for good ones, tags on every day, period days marked underneath.

**Your history, answered**
- Ask things like "What helped my acidity last time?" or "Why have I been tired lately?" Ruvia looks through your own records first and answers from them.
- Your usual levels, a weekly "what changed" summary, and patterns like "Headache on 9 of 12 low water days". Patterns only show after three weeks of data, and they show counts, not made up confidence.
- Weather from Open-Meteo, so it can spot links like headaches on days the air pressure drops.
- A doctor summary PDF with symptoms, what helped, medicines and questions worth asking.

**Family**
- A care circle. Each person picks what to share with each other person: scores, tags, symptoms, water, cycle, health dates, emergency card, medicines. Everything starts off except the rough day signal. Anything can be turned off at any time.
- Gentle check-ins: your partner can know you had a rough day without seeing why.
- Send a hug, a water reminder, or "how are you?" to someone in your circle.
- Shared goals with a weekly grid for each person, and a shared calendar of health dates.

**Everything else**
- Emergency card that works offline, with one tap calls to your contacts.
- Home medicine cabinet, so suggestions mention what you already have.
- Reminders set by each person: how many check-ins a day, how far apart, and quiet hours.
- Works offline. Check-ins and water logged without signal sync when you are back.
- Light mode and a deep ocean dark mode that follows your device.
- Export everything as JSON, or delete your account and all of its data.

## Built with

| Part | What |
| --- | --- |
| Backend | Python 3.12, Django 5.2, Django REST Framework, Simple JWT |
| Frontend | React 18, Vite, a hand written service worker with Workbox, Framer Motion |
| Database | PostgreSQL on Neon (SQLite locally) |
| Hosting | Render for the API, Vercel for the app |
| Email | SendGrid, for sign up codes, sign in codes and password resets |
| Language models | OpenAI first, then Google Gemini, then Anthropic Claude if one errors or times out |
| Voice | OpenAI Whisper |
| Push | Web Push with VAPID keys |
| Weather | Open-Meteo, free and keyless |
| Reminders | A scheduler run every 10 minutes by a Render cron job or a free GitHub Actions schedule |
| PDF | ReportLab |

Without any model keys the app still works. Check-ins are read with keyword rules and replies come from templates, so the demo runs out of the box.

## Try it

Two demo accounts come with plenty of history so every screen has something to show:

| Who | Email | Password |
| --- | --- | --- |
| Jane | demoruvia@yopmail.com | RuviaDemo2026! |
| Joe | demo1ruvia@yopmail.com | RuviaDemo2026! |

Joe is Jane's husband and in her care circle. She shares her scores, tags, water, cycle, rough days, health dates and emergency card with him, but not her symptom details or medicines, so you can see how sharing works from both sides.

Yopmail inboxes are public, so never put real information into these accounts.

## Run it on your computer

You need Python 3.12 and Node 20 or newer.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # DEBUG=true is enough to start
python manage.py migrate
python manage.py seed_demo
python manage.py runserver      # http://localhost:8000

# Frontend, in a second terminal
cd frontend
cp .env.example .env
npm install
npm run dev                     # http://localhost:5173
```

Without a SendGrid key, sign up codes are printed in the backend terminal.

Run the tests with `python manage.py test health`.

## Project layout

```
backend/
  accounts/     users, email codes, sign in
  health/       days, water, tags, symptoms, medicines, cycle, insights, PDF
    services/   library.py (all suggestions), safety.py, remedies.py, insights.py, cycle.py
  assistant/    check-in pipeline, model fallback, history questions, follow-ups
  care/         care circle, sharing permissions, nudges
  notify/       inbox, web push, the scheduler
frontend/
  src/pages/    one file per screen
  src/sw.js     offline support and push notifications
render.yaml     Render blueprint
.github/        free reminder schedule
```

Everything Ruvia suggests lives in `backend/health/services/library.py`: symptoms, home remedies, over the counter options, medicine interaction rules, mood suggestions and cycle tips. Read it and change anything you like. No model decides what is safe.

## A note on privacy

Check-in text and notes are encrypted in the database. The text of a check-in is sent to the model providers to be read and replied to, without names or emails. Voice notes go to OpenAI for transcription. The privacy screen in the app says this in plain words.

Ruvia is a diary and a gentle helper, not a doctor. If something feels serious, call 911, or 811 for Health811 in Ontario.

## Deploying

See [DEPLOY.md](DEPLOY.md) for step by step instructions for Neon, Render, Vercel, SendGrid and push reminders.

Made by [Ashray Sikka](https://ashraysikka.com), for Grusha.
