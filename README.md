# Reel & Post Downloader
Instagram + X (Twitter) media downloader. Flask + yt-dlp.

## Local
pip install -r requirements.txt && flask --app app run

## Railway
1. Push to GitHub, Railway -> New Project -> Deploy from GitHub.
2. Procfile start command use ho jayega.
3. Optional: Instagram block kare to `IG_COOKIES` variable me Netscape cookies.txt ka content daalo (alag/burner account se export karo).
4. Time-time pe `pip install -U yt-dlp` (redeploy) karo, IG/X baar baar change hote hain.
