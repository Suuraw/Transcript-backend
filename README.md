# 📜 Transcript-backend

A lightweight backend service to:

- ✅ **Fetch YouTube video transcripts**
- ✅ **Generate concise summaries**
- ✅ **Create question sets based on summaries**

---

## 📈 Performance Highlights

- ⚡ **Fast Transcript Fetching:** ~1.66 seconds per request
- ⚡ **Efficient Summarization:** ~55 seconds for a 4-hour long video
- ⚡ **Questionnaire Generation:** Instantly creates relevant questions from video summaries

---

## ⚠️ Limitations

- ❌ **Not Suitable for Production Deployment:** YouTube blocks IP addresses from most cloud providers.
- 🌐 **Works Only with Residential IPs:** For consistent transcript fetching, run the service on a home network or device with a residential IP.

---

## 🧠 Features

- 🔍 **Transcript Extraction** — Pulls subtitles/transcripts from any YouTube video
- ✨ **Smart Summarization** — handle very large transcripts text and provide concise summary
- ❓ **Auto-Questionnaire** — Generates questions from the summary to aid learning or quizzing

---

## Prerequisites

- **Docker** installed on your machine
- Access to **Google Cloud Console** to obtain the API key for Gemini Flash

---

## ⚙️ Docker Desktop Settings (Windows/macOS)

1. Open **Docker Desktop**
2. Navigate to **Settings → General**
3. ✅ Enable: **"Start Docker Desktop when you log in"**
4. Click **Apply & Restart** if prompted

> Ensures Docker starts automatically with system reboot. Needed for containers with `--restart unless-stopped`.

---

## Setup Instructions

> You can **either build from source** or **just pull and run the image** directly.

---

### 🛠 Option 1: Clone & Build the Image

```bash
git clone https://github.com/Suuraw/Transcript-backend
cd Transcript-backend
```

Create a `.env` file in the project root with:

```env
API_TOKEN=mytranscripts
GEMINI_API_KEY=YOUR_API_KEY
```

Then:

```bash
docker build -t transcript-image .
docker run -d \
  -p 8000:8000 \
  --name transcript-container \
  --env-file .env \
  --restart unless-stopped \
  transcript-image
```

---

### 🐳 Option 2: Pull & Run Prebuilt Docker Image (Recommended)

> ✅ Make sure you are in the **same directory as your `.env` file**, which includes your `API_TOKEN` and `GEMINI_API_KEY`.

```bash
docker pull suuraw/transcript-backend:latest
```

Then run:

```bash
docker run -d \
  -p 8000:8000 \
  --name transcript-container \
  --env-file .env \
  --restart unless-stopped \
  suuraw/transcript-backend:latest
```

---

## 📂 `.env` File Format

Ensure your `.env` looks like this:

```env
API_TOKEN=mytranscripts
GEMINI_API_KEY=YOUR_API_KEY
```

Replace `YOUR_API_KEY` with the actual Gemini API key from your Google Cloud Console.

---

## 🔍 Test the Service

**Frontend Website** – [https://www.watch2learn.app/](https://www.watch2learn.app/)

- ### 🧪 Dev Access Credentials:
  ```
  1234
  ```

---

## 📞 Support

Encountering issues or want to contribute?  
👉 [Open an issue](https://github.com/Suuraw/Transcript-backend/issues) on the GitHub repo.

---

**_HAPPY TRANSCRIBING, SUMMARIZING & QUESTIONING!_**
