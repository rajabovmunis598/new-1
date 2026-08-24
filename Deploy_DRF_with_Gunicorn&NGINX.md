# Django Deployment Tutorial (Ubuntu + Gunicorn + Nginx + SSL)
Full step-by-step guide from cloning the project → to production
## Step 1 — Connect to Server & Clone the Project
1. SSH into your server
ssh admin@YOUR_SERVER_IP

2. Create a folder for your project
mkdir ~/my_project
cd ~/my_project

3. Generate an SSH key (required for cloning private GitHub repo)
ssh-keygen -t ed25519 -C "your_email@example.com"


Press Enter for all prompts.

4. View your public key
cat ~/.ssh/id_ed25519.pub


Copy the key.

5. Add SSH key to GitHub

GitHub →
Settings → SSH and GPG Keys → New SSH Key → paste → Save

6. Clone your private GitHub repository
git clone git@github.com:username/repo_name.git .

## Step 2 — Create Virtual Environment & Install Dependencies
1. Create venv
python3 -m venv .venv

2. Activate
source .venv/bin/activate

3. Install project dependencies
pip install -r requirements.txt

## Step 3 — Configure STATIC and MEDIA in settings.py

Before running migrations or collectstatic, you MUST configure static/media.

Open:

nano project/settings.py


Add:

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- STATIC ----------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

# ---------- MEDIA ----------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


Explanation:

STATIC_ROOT — final folder where Django collects all static files.

MEDIA_ROOT — folder for uploaded files.

## Step 4 — Apply Migrations and Collect Static Files
1. Run migrations
python manage.py migrate

2. Collect static files
python manage.py collectstatic

3. Test project
python manage.py runserver 0.0.0.0:8000


If it works — continue.

## Step 5 — Install & Configure Gunicorn
1. Install Gunicorn
pip install gunicorn

2. Create Gunicorn systemd service

File:

/etc/systemd/system/my_project.service


Open:

sudo nano /etc/systemd/system/my_project.service


Paste:

[Unit]
Description=Gunicorn daemon example.tj
After=network.target

[Service]
User=admin
Group=www-data
WorkingDirectory=/home/admin/my_project
ExecStart=/home/admin/my_project/.venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind 0.0.0.0:8000 server.wsgi:application

[Install]
WantedBy=multi-user.target

3. Start and enable service

sudo systemctl daemon-reload
sudo systemctl start my_project.service
sudo systemctl enable my_project.service
sudo systemctl status my_project.service


If something fails:

sudo journalctl -u my_project.service -n 50 --no-pager

## Step 6 — Install and Configure Nginx
1. Install Nginx
sudo apt update
sudo apt install nginx

2. Create Nginx config

File:

/etc/nginx/sites-available/my_project


Open:

sudo nano /etc/nginx/sites-available/my_project


Paste:

server {
    listen 80;
    server_name example.tj;

    location /static/ {
        root /home/admin/my_project;
    }

    location /media/ {
        root /home/admin/my_project;
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
    }
}

3. Enable site
sudo ln -s /etc/nginx/sites-available/my_project /etc/nginx/sites-enabled/

4. Test configuration
sudo nginx -t

5. Reload Nginx
sudo systemctl reload nginx
sudo systemctl restart nginx
sudo systemctl status nginx

6. If problems occur — check logs
sudo tail -f /var/log/nginx/error.log

## Step 7 — Install SSL Certificates (HTTPS)
1. Install Certbot
sudo apt install certbot python3-certbot-nginx

2. Generate SSL certificate
sudo certbot --nginx -d example.tj


Certbot will:

enable HTTPS
q
configure redirect

reload Nginx

3. Verify
sudo systemctl status nginx


# Troubleshooting: CSS/JS Not Loading (Static Files Issues)

If your website opens but CSS, JS, or images do not appear, this usually means Nginx cannot read your static files.
Below are the steps to diagnose and fix the problem.

1. Check Nginx error logs

Run this command to see real-time errors:

sudo tail -f /var/log/nginx/error.log


If Nginx cannot read a static file, you will see an error like:

open() "/home/admin/my_project/static/rest_framework/css/default.css" failed (13: Permission denied)


This confirms a permissions problem.

2. Common Reasons Why CSS/JS Are Not Loading
Reason 1 — Nginx does not have permission to read your project folders

Nginx runs as:

www-data


This user must have “execute” (x) access to:

/home
/home/admin
/home/admin/my_project
/home/admin/my_project/static


If any folder blocks access → CSS will not load.

Reason 2 — Wrong ownership of project files

If your project belongs only to your user and not to www-data,
Nginx cannot read it.

Reason 3 — Incorrect STATIC_ROOT or Nginx static path

If Django collected static files into:

/home/admin/my_project/static


but your Nginx config points somewhere else, files will not load.

Reason 4 — You forgot to run collectstatic

Static folder may simply be empty.

3. How to Fix Permission Problems
✔️ Fix 1 — Set correct owner and group

Make your project readable by Nginx:

sudo chown -R admin:www-data /home/admin/my_project

✔️ Fix 2 — Allow Nginx to enter directories

Apply correct permissions:

sudo chmod 755 /home
sudo chmod 755 /home/admin
sudo chmod 755 /home/admin/my_project


This is safe and required.

✔️ Fix 3 — Allow reading static and media
sudo chmod -R 755 /home/admin/my_project/static
sudo chmod -R 755 /home/admin/my_project/media

✔️ Fix 4 — Restart Nginx
sudo systemctl restart nginx

4. After Applying Fixes

Refresh your website.

If something still doesn’t load, watch logs again:

sudo tail -f /var/log/nginx/error.log


If no more permission errors appear — the issue is fully resolved.