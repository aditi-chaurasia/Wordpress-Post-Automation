# WordPress News Automation - Dual Cron System

Automated Hindi news content generation and publishing system with optimized intervals for different content types:
- **Multi-source News**: Every 45 minutes
- **Viral & UP News**: Every 3 hours
- **Image Retry**: Every 6 hours

## 🚀 **Quick Setup**

1. **Clone Repository**
   ```bash
   git clone https://github.com/A-Consult/wp-news.git
   cd wp-news
   ```

2. **Update Configuration**
   ```bash
   nano config.json
   # Update WordPress credentials and API keys
   ```

3. **Deploy to Ubuntu Server**
   ```bash
   chmod +x setup_dual_cron.sh
   ./setup_dual_cron.sh
   ```

4. **Test & Monitor**
   ```bash
   # Test individual components
   ./test_multi_source.sh
   ./test_viral_up.sh
   
   # Monitor the system
   ./monitor_dual_automation.sh
   ```

## 📁 **Essential Files**

- **`wordpress.py`** - Main automation script with dual functionality
- **`scheduler.py`** - Enhanced scheduler with separate content type handling
- **`setup_dual_cron.sh`** - New Ubuntu server setup script for dual cron
- **`config.json`** - Configuration file
- **`requirements.txt`** - Python dependencies
- **`processed_trends.json`** - Tracks processed trends
- **`predefined_images/`** - Categorized images by topic
- **`logs/`** - Individual run logs for each content type

## ⚙️ **Features**

### Multi-source News (45-minute intervals)
- ✅ Multiple Hindi news sources monitoring
- ✅ Standard AI content generation
- ✅ Categories: National, World, Technology, Sports, etc.
- ✅ 3 posts per run

### Viral & UP News (3-hour intervals)
- ✅ Dedicated viral news tracking
- ✅ Enhanced content generation with search grounding
- ✅ Categories: वायरल (Viral) and उत्तर प्रदेश (UP)
- ✅ 5 posts per run
- ✅ Special author assignment for UP news

### Common Features
- ✅ AI-powered content generation (1000+ words per article)
- ✅ Dynamic image selection/generation
- ✅ WordPress API integration
- ✅ Duplicate content prevention
- ✅ Comprehensive logging per content type

## 📊 **Automation Schedule**

### Multi-source News
- **Interval**: Every 45 minutes (0, 15, 30, 45)
- **Content**: Regular news articles
- **Sources**: Multiple RSS feeds (Bhaskar, NDTV, News18, etc.)

### Viral & UP News
- **Interval**: Every 3 hours (0:00, 3:00, 6:00, 9:00, 12:00, 15:00, 18:00, 21:00)
- **Content**: Viral trends and UP-specific news
- **Sources**: Dedicated viral and UP feeds

### Image Retry
# WordPress Post Automation — Dual Cron

A compact, production-oriented automation for Hindi news publishing to WordPress. The project runs separate schedules for different content types (multi-source news, viral/UP news, image retry) and integrates AI-generated content, dynamic image handling, and WordPress REST API publishing.

## Quick overview

- Multi-source news: every 45 minutes
- Viral & UP news: every 3 hours
- Image retry: every 6 hours

## Quick start

Prerequisites:
- Ubuntu server (18.04+), or any Linux host
- Python 3.8+
- A WordPress site with REST API and an application password
- Required API keys (Google Gemini / image generator)

Steps:

1. Clone the repository

```bash
git clone https://github.com/A-Consult/wp-news.git "post-automation"
cd "post-automation"
```

2. Create and activate a virtual environment, then install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Update configuration

Edit `config.json` with your WordPress credentials and API keys (see Configuration below).

4. (Optional) Run the setup script for Ubuntu servers

```bash
chmod +x setup_dual_cron.sh
./setup_dual_cron.sh
```

5. Test components / monitor

```bash
./test_multi_source.sh
./test_viral_up.sh
./monitor_dual_automation.sh
```

## Important files

- `wordpress.py` — main publishing automation
- `scheduler.py` — scheduler and command-line entry
- `config.json` — central configuration (credentials, API keys)
- `requirements.txt` — Python dependencies
- `predefined_images/` — categorized images used by the generator
- `logs/` — runtime logs

## Configuration example

Copy or edit `config.json` to include your credentials (minimal example):

```json
{
   "wordpress": {
      "site_url": "https://your-website.com",
      "username": "your_username",
      "password": "your_app_password"
   },
   "gemini": { "api_key": "your_gemini_api_key" },
   "image_generator": { "api_key": "your_image_api_key" },
   "automation": { "max_posts_per_run": 3, "country": "IN" }
}
```

Keep this file private — do not commit API keys or passwords.

## Running & testing

- Start a single run via scheduler

```bash
python3 scheduler.py run_multi_source
python3 scheduler.py run_viral_up
python3 scheduler.py image_retry
```

- View logs

```bash
tail -f logs/scheduler.log
ls -la logs/
```

## Deployment notes

- The repository includes `setup_dual_cron.sh` to create appropriate cron entries on Ubuntu. Review the script before running.
- On servers, run under a dedicated user and use a virtual environment.
- Ensure the WordPress application password has appropriate capabilities to create posts.

## Troubleshooting

- Missing Python imports: activate the virtualenv and run `pip install -r requirements.txt`.
- WordPress auth errors: verify `site_url`, username, and application password in `config.json`.
- Cron jobs not executing: check `crontab -l` and system cron logs (`/var/log/syslog`).

## Documentation & references

- See `DUAL_CRON_DEPLOYMENT_GUIDE.md` for full deployment steps.
- See `DUAL_CRON_SUMMARY.md` for a compact reference.

---

If you'd like, I can also:

- create a `.gitignore` entry to exclude `config.json` and `venv/`
- commit these README changes and make a GitHub push (I can run commands for you)

File updated: [README.md](README.md)





