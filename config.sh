sudo apt update && sudo apt upgrade -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv -y
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install python-socketio
sudo apt update
sudo apt install supervisor -y
sudo cp config/supervisor.conf /etc/supervisor/conf.d/zvms.conf
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start zvms
sudo supervisorctl status
sudo apt install supervisor -y
sudo cp config/nginx.conf /etc/nginx/sites-available/zvms
sudo ln -s /etc/nginx/sites-available/zvms /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.zvms.site
sudo certbot renew --dry-run
sudo tail -f /var/log/zvms.out.log
sudo tail -f /var/log/nginx/zvms.log
