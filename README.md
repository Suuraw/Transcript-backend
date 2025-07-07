# 📜 Transcript-backend

A lightweight backend service to **fetch YouTube video transcripts** and **generate concise summaries** using Google's Gemini Flash models via GenAI API.

---

## 📈 Performance Highlights

- ✅ **Fast Transcript Fetching:** ~1.66 seconds per request  
- ✅ **Efficient Summarization:** ~55 seconds for a 4-hour long video  

---

## ⚠️ Limitations

-  **Not Suitable for Production Deployment:** YouTube blocks IP addresses from most cloud providers.  
-  **Works Only with Residential IPs:** The transcript fetching works reliably only when hosted on a machine with a residential IP (e.g., home internet).

---
## Prerequisites

- **Docker** must be installed on your machine.
- Access to **Google Cloud Console** to obtain the API key for **Gemini Flash models**.

---

## ⚙️ Docker Desktop Settings (Windows/macOS)

To ensure Docker starts automatically and runs containers in the background without manual intervention:

1. **Open Docker Desktop**.
2. Navigate to **Settings** → **General**.
3. ✅ Enable: **"Start Docker Desktop when you log in"**.
4. Click **Apply & Restart** if prompted.

> This ensures Docker starts with the system and containers configured with `--restart unless-stopped` will run automatically.

---

## Setup Instructions

### Step 1: Clone the Repository

```bash
git clone https://github.com/Suuraw/Transcript-backend
cd Transcript-backend
```

---

### Step 2: Get Your GenAI API Key

- Visit [Google Cloud Console](https://console.cloud.google.com/)
- Navigate to your Gemini Flash project
- Generate an **API key** for model access

---

### Step 3: Create a `.env` File

Create a `.env` file in the root of the project directory and add the following content:

```env
API_TOKEN=mytranscripts
GEMINI_API_KEY=YOUR_API_KEY
```

> Replace `YOUR_API_KEY` with the actual key you got from GCP.

---

### 🐳 Step 4: Build & Run the Docker Container

#### 1. Build the Docker Image

```bash
docker build -t transcript-image .
```

#### 2. Run the Container in Detached Mode

```bash
docker run -d \
  -p 8000:8000 \
  --name transcript-container \
  --env-file .env \
  --restart unless-stopped \
  transcript-image
```

This command will:
- Bind the container's port `8000` to your local port `8000`
- Load environment variables from `.env`
- Ensure the service restarts automatically on failure or reboot

---

## 📞 Support

If you encounter any issues or have questions, feel free to [open an issue](https://github.com/Suuraw/Transcript-backend/issues) on the repository.
