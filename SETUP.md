# Home Finder Agent — Setup Guide

Complete these steps once. After setup, the agent runs itself every morning at 8am.

---

## Step 1: Create the RC-KBHomes Gmail Account

1. Go to https://accounts.google.com/signup
2. Choose the username **RC-KBHomes** (or similar if taken)
3. Complete account creation
4. Once logged in, go to: https://myaccount.google.com/security
5. Turn on **2-Step Verification** (required for App Passwords)
6. After enabling 2-Step Verification, go to: https://myaccount.google.com/apppasswords
7. Under "Select app" choose **Mail**, under "Select device" choose **Other** and type `HomeFinder`
8. Click **Generate** — copy the 16-character password shown (you will need it in Step 4)

---

## Step 2: Create a Free RapidAPI Account

1. Go to https://rapidapi.com and click **Sign Up**
2. Once logged in, search for **"Zillow"** → find "Zillow Com1" → click **Subscribe to Test** (Basic/Free plan)
3. Search for **"Realty in US"** → find "Realty In US" → click **Subscribe to Test** (Basic/Free plan)
4. Go to https://rapidapi.com/developer/apps → click your app → copy the **X-RapidAPI-Key** value

---

## Step 3: Create a Free Google Cloud Account

1. Go to https://console.cloud.google.com and sign in with any Google account
2. Click **Create Project** → name it `HomeFinder`
3. In the search bar at top, type **Directions API** → click it → click **Enable**
4. In the left menu, go to **APIs & Services → Credentials**
5. Click **Create Credentials → API Key** → copy the key shown

---

## Step 4: Create the GitHub Repository

1. Log into your GitHub account
2. Click the **+** button (top right) → **New repository**
3. Name it `home-finder` → set to **Private** → click **Create repository**
4. On your Mac, open Terminal and run these commands one at a time:
   ```
   cd "/Users/richardcaron/App Projects/Home Finder 1.0"
   git remote add origin https://github.com/YOUR-USERNAME/home-finder.git
   git push -u origin main
   ```
   Replace YOUR-USERNAME with your actual GitHub username.

---

## Step 5: Add Your Secret Keys to GitHub

1. In your GitHub repository, click **Settings** (top menu)
2. In the left sidebar, click **Secrets and variables → Actions**
3. Click **New repository secret** for each of the following:

| Secret Name | Value |
|---|---|
| `RAPIDAPI_KEY` | Your RapidAPI key from Step 2 |
| `GOOGLE_MAPS_API_KEY` | Your Google Maps API key from Step 3 |
| `GMAIL_APP_PASSWORD` | The 16-character App Password from Step 1 |
| `DASHBOARD_URL` | Leave blank for now — fill in after Step 6 |

---

## Step 6: Enable GitHub Pages (Your Free Website)

1. In your GitHub repository, click **Settings**
2. In the left sidebar, click **Pages**
3. Under "Source", select **Deploy from a branch**
4. Under "Branch", select **main** and folder **/ (root)** → click **Save**
5. Wait 2 minutes, then your dashboard URL will appear at the top of the Pages settings page
6. Copy that URL (looks like `https://YOUR-USERNAME.github.io/home-finder`)
7. Go back to **Settings → Secrets and variables → Actions**
8. Edit the `DASHBOARD_URL` secret and paste that URL

---

## Step 7: Run the Agent for the First Time

1. In your GitHub repository, click **Actions** (top menu)
2. Click **Daily Home Finder Run** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Wait 3–5 minutes for it to finish
5. Click the completed run to see the log output
6. Check your email — your first digest will arrive shortly after

From this point on, the agent runs automatically every morning at 8am and emails you only new listings.

---

## How to Change Settings

Open `config.json` in your repository and edit any values. Click the pencil icon on GitHub to edit directly — no software needed. Changes take effect on the next daily run.

## How to Add or Remove Email Recipients

Open `subscribers.json` and add or remove email addresses from the list. Edit directly on GitHub with the pencil icon.

## To Unsubscribe

Reply to any digest email with the word **STOP**. The sender (RC-KBHomes@gmail.com) will receive it and remove your address from `subscribers.json`.
