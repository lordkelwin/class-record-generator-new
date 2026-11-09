# USeP OBE Syllabus-to-Class Record Generator
## Local Server Deployment & Client User Acceptance Testing (UAT) Guide

This guide details how to launch, configure, and test the **USeP OBE Syllabus-to-Class Record Generator** locally on a host machine (`localhost`) and across a Local Area Network (LAN / Wi-Fi) for multi-user client acceptance testing.

---

### 1. Quick Start (1-Click Launch)

#### Windows (Recommended for Client UAT)
Double-click the startup script in the project root folder:
```cmd
start_local_server.bat
```
*What the script does automatically:*
1. Detects Python (virtual environment `.venv`/`venv` or system Python 3.10+).
2. Verifies and installs missing dependencies from `requirements.txt`.
3. Discovers the machine's local network (LAN) IP address.
4. Binds the server to `0.0.0.0:5000` (accessible from both `localhost` and other network devices).
5. Displays clear access URLs and admin credentials in the console window.

#### Linux / macOS
Open a terminal in the project directory and run:
```bash
chmod +x start_local_server.sh
./start_local_server.sh
```
*(Alternatively: `python app.py`)*

---

### 2. Accessing the Web Application

When the server starts, it prints a banner similar to:
```
======================================================================
  USeP OBE Syllabus-to-Class Record Generator - Local Server
======================================================================
  Server is active and ready for Client User Acceptance Testing (UAT):

  👉 Local Machine (This PC):
     http://localhost:5000
     http://127.0.0.1:5000

  👉 Network / LAN Access (Same Wi-Fi or Local Network):
     http://192.168.1.50:5000

  Default Faculty & Admin Credentials:
     Admin Username   : admin
     Admin Password   : admin123
======================================================================
```

#### Access Types
| Access Type | URL Example | Description |
|---|---|---|
| **Local Machine** | `http://localhost:5000` | Open directly in any browser on the computer running the server. |
| **LAN / Wi-Fi Devices** | `http://<HOST-IP>:5000` | Open from any phone, laptop, or tablet connected to the same Wi-Fi/LAN. |

> [!TIP]
> **To find your host machine's LAN IP address manually:**
> - **Windows:** Open Command Prompt and run `ipconfig`. Look for **IPv4 Address** (e.g. `192.168.1.50`).
> - **macOS / Linux:** Run `ifconfig` or `ip a` (look for `inet` under `en0` or `wlan0`).

> [!NOTE]
> **Windows Defender Firewall Note (For Multi-Device Testing):**
> If other devices on the same Wi-Fi cannot connect to `http://<HOST-IP>:5000`, allow Python through Windows Firewall or add an inbound port rule:
> 1. Open Windows Search &rarr; type `Windows Defender Firewall with Advanced Security`.
> 2. Select **Inbound Rules** &rarr; **New Rule...**
> 3. Choose **Port** &rarr; **TCP** &rarr; Specific local ports: `5000`.
> 4. Select **Allow the connection** &rarr; click **Next** through Domain/Private/Public &rarr; Name: `USeP OBE Server 5000` &rarr; **Finish**.

---

### 3. Default Testing Personas & Credentials

The application includes pre-configured testing roles matching the official USeP faculty and administrative hierarchy:

| Role / Persona | Username | Password | Purpose & Capabilities |
|---|---|---|---|
| **System Administrator** | `admin` | `admin123` | Full access: manage faculty accounts, unlock workflows, system oversight. |
| **Faculty Member (Author)** | `elwin.tano` | `faculty123` | Syllabus creator, class record grade entry, auto-calculations, export PDFs. |
| **Review Committee Chair** | `nikka.basan` | `faculty123` | Syllabus review checklist evaluation, feedback, signatory sign-off. |
| **Program Head** | `charito.claro` | `faculty123` | Syllabus endorsement, course-to-program alignment review. |
| **College Dean** | `joie.cataytay` | `faculty123` | Final syllabus approval, signatory sealing, class record oversight. |
| **Student Portal** | `2025-00132` | `student123` | Access student portal (`/student/login`), review grade performance, sign acknowledgments. |

---

### 4. Environment & Database Configuration (`.env`)

A sample configuration file [`.env.example`](file:///.env.example) is provided. To customize settings, copy it to `.env`:

```env
# Network settings
HOST=0.0.0.0
PORT=5000
DEBUG=false

# Database paths (uses defaults in ./data if unset)
# DATABASE_PATH=data/academic_catalog.db
# DATA_DIR=data
# COURSES_DIR=data/courses
# USERS_JSON_PATH=data/users.json
# STUDENTS_JSON_PATH=data/students.json

# Microsoft Access Curriculum Database
# ACCDB_PATH=prospectus/PGO-PI-IGA.accdb
```

#### Database Architecture & Offline Readiness:
1. **SQLite Database (`data/academic_catalog.db`):**
   - Stores catalog programs, course descriptions, prerequisites, corequisites, and relational tables.
   - Fully portable and self-contained; requires zero external server setup.
2. **Microsoft Access Database (`prospectus/PGO-PI-IGA.accdb`):**
   - Authoritative source for BSEE curriculum, course descriptions, and PGO-PI-IGA mappings.
   - Accessed via direct SQL ODBC on Windows machines with Microsoft Access driver.
   - **Automatic Graceful Fallback:** If Access ODBC driver is not installed on the client machine, the system automatically falls back to the authoritative in-memory Python catalog without crashing.
3. **Typography & Font Assets (`fonts/`):**
   - Includes **Cinzel Bold** (`fonts/Cinzel-Bold.otf`) for Controlled Document headers (e.g., FM-USeP-MID-01, FM-USeP-MID-02, FM-USeP-MID-07).
   - Embedded locally so official PDF outputs render pixel-perfect without requiring Windows font installation.
4. **Self-Contained Client Assets:**
   - All styling, scripting, and icons are bundled locally with zero reliance on external CDNs, ensuring full functionality in air-gapped or offline testing environments.

---

### 5. Troubleshooting & FAQ

- **Port Conflict (`Address already in use`):**
  If port 5000 is occupied by another application (e.g. AirPlay on macOS or another service), you can launch on port 8000 or 3000 by setting `PORT=8000` in `.env` or running:
  ```cmd
  set PORT=8000 && python app.py
  ```
- **Session Persistence Across Devices:**
  Session cookies are configured with `SameSite=Lax` and `HttpOnly=True` without enforcing HTTPS, allowing seamless multi-device testing over plain HTTP on LAN IP addresses.
