# RegAdmin

Flask app for staff to create events and register guests as existing or new members.

## Features

- Staff authentication (sign in / create staff account)
- Event creation with **date** and **venue**
- Registrations tied to each event
- Existing member vs new member selection
- Dashboard, event detail, and registration filters

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Open `http://127.0.0.1:5000`.

Default admin (created automatically from `.env`):

- Username: `admin`
- Password: `admin123`

## Typical flow

1. Sign in as staff
2. Create an event (name, date, venue)
3. Register a user for that event
4. Choose **Existing member** or **New member**
5. View registrations from the event page or the Registrations list

## Deploy on Render

This repo includes `render.yaml` for a free web service + Postgres database.

1. Push to GitHub
2. In [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect the `regadmin` repo and apply the blueprint
4. After deploy, open the service **Environment** tab and copy `ADMIN_PASSWORD` (auto-generated)
5. Sign in with username `admin` and that password

Manual deploy (without Blueprint): create a **Web Service**, set build `pip install -r requirements.txt`, start `gunicorn "run:app" --bind 0.0.0.0:$PORT`, add a Postgres database, and set `DATABASE_URL`, `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.
