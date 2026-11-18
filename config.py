"""
Centralized Configuration and Environment Loader for USeP OBE Studio.
Provides portable, environment-driven paths and network settings for local/LAN UAT.
"""

import os
import socket
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_env(env_file: str = ".env") -> None:
    """
    Loads environment variables from a .env file without external dependencies.
    Existing system environment variables take precedence.
    """
    env_path = os.path.join(BASE_DIR, env_file)
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
            logger.info(f"Loaded environment variables from {env_path}")
        except Exception as e:
            logger.warning(f"Error reading {env_path}: {e}")


# Load .env file automatically on import
load_env()


def get_local_ip() -> str:
    """
    Discovers the local area network (LAN) IP address of the host machine.
    Used for multi-user client testing on the same Wi-Fi or LAN.
    Prefers active default-route interface IP, falling back to non-loopback IPv4 interface scan.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        candidates = []
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            addr = info[4][0]
            if addr and not addr.startswith("127.") and not addr.startswith("169.254."):
                candidates.append(addr)
        # Prefer standard private LAN subnets (192.168.*, 10.*, 172.16-31.*)
        for prefix in ("192.168.", "10."):
            for c in candidates:
                if c.startswith(prefix):
                    return c
        if candidates:
            return candidates[0]
        fallback = socket.gethostbyname(hostname)
        if fallback and not fallback.startswith("127."):
            return fallback
    except Exception:
        pass
    return "127.0.0.1"


# Network settings (0.0.0.0 binds to all network interfaces for LAN & Cloud Run)
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")

# Cloud / Firebase Pilot Deployment settings
USE_FIREBASE = os.environ.get("USE_FIREBASE", "false").lower() in ("true", "1", "yes")
GCLOUD_PROJECT_ID = os.environ.get("GCLOUD_PROJECT_ID", "usep-faculty-student")
FIREBASE_PROJECT_ID = os.environ.get(
    "FIREBASE_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", "faculty-student-studio-usep")
)
FIREBASE_PROJECT_NUMBER = os.environ.get("FIREBASE_PROJECT_NUMBER", "621897460998")
FIREBASE_STORAGE_BUCKET = os.environ.get(
    "FIREBASE_STORAGE_BUCKET", "faculty-student-studio-usep.firebasestorage.app"
)
FIRESTORE_DATABASE_ID = os.environ.get("FIRESTORE_DATABASE_ID", "(default)")

FIREBASE_WEB_CONFIG = {
    "apiKey": os.environ.get("FIREBASE_WEB_API_KEY", "AIzaSyCYekPVvbg_4ViOBlXqPHtRYpKqdVPF4V8"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", "faculty-student-studio-usep.firebaseapp.com"),
    "projectId": FIREBASE_PROJECT_ID,
    "storageBucket": FIREBASE_STORAGE_BUCKET,
    "messagingSenderId": FIREBASE_PROJECT_NUMBER,
    "appId": os.environ.get("FIREBASE_APP_ID", "1:621897460998:web:f2566ff727e1c7630d0287"),
    "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID", "G-LS3E68ZLQQ"),
}

# Database & Data storage paths
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "academic_catalog.db"))
USERS_JSON_PATH = os.environ.get("USERS_JSON_PATH", os.path.join(DATA_DIR, "users.json"))
STUDENTS_JSON_PATH = os.environ.get("STUDENTS_JSON_PATH", os.path.join(DATA_DIR, "students.json"))
COURSES_DIR = os.environ.get("COURSES_DIR", os.path.join(DATA_DIR, "courses"))
SECRET_KEY_FILE = os.environ.get("SECRET_KEY_FILE", os.path.join(DATA_DIR, "secret_key"))
ACCDB_BUNDLE_PATH = os.environ.get(
    "ACCDB_BUNDLE_PATH", os.path.join(DATA_DIR, "accdb_curriculum_bundle.json")
)

# Microsoft Access Curriculum Database (PGO-PI-IGA.accdb)
ACCDB_PATH = os.environ.get("ACCDB_PATH", os.path.join(BASE_DIR, "prospectus", "PGO-PI-IGA.accdb"))
ACCDB_CONN_STR = os.environ.get(
    "ACCDB_CONN_STR",
    f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ACCDB_PATH};"
)

# Typography & Font Assets
FONTS_DIR = os.environ.get("FONTS_DIR", os.path.join(BASE_DIR, "fonts"))
CINZEL_FONT_PATH = os.environ.get("CINZEL_FONT_PATH", os.path.join(FONTS_DIR, "Cinzel-Bold.otf"))
