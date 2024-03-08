# config.py - Configurations related to image storage
# What? You say it's redundant with settings.py? Well, it's redundant, I'm too lazy to change it. I'll talk about it later, it's okay to run.

# Storage methods
STORAGE = "" # Storage method, xuehai or backblaze
XUEHAI_URL = "" # URL of xuehai
KEYID = "" # Key ID of backblaze
KEYNAME = "" # Key name of backblaze
APPKEY = "" # Application key of backblaze
BASEURL = "" # Base URL of backblaze
CFURL = "" # Cloudflare Proxy URL of backblaze

# Database parameters
DB_PATH = "" # Database file path

# Image upload parameters
UPLOAD_FOLDER = "" # Cache folder for image upload
PAGE_SIZE = 10 # Number of images per page
PAGE_NUM = 1 # Number of pages
MAX_SIZE = 3 * 1024 * 1024 # Maximum image size

# Image checking parameters
CHECK_ENABLED = False # Whether to enable image checking
KEYWORDS_GENERATE_ENABLED = False # Whether to enable keywords generation
HF_ENABLED = False # Whether to enable HF model
HF_URL = "" # HF model URL

# Service parameters | From [zvms/skyView] and didn't modified by @diyanqi
SERVERURL = "" # Server URL
SUPERADMINTOKEN = ""
host = "" # Server host
port = 6666 # Server port
