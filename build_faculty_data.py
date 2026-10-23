"""
Builds and synchronizes all official faculty accounts, roles, titles, and signatures
from the updated 'FACULTY PROGRAM LIST - 1ST  SEM S.Y. 26-27.docx.pdf'.
"""

import os
import json
import base64
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
SIG_DIR = os.path.join(BASE_DIR, "static", "signatures")

# Load real signatures
with open(os.path.join(SIG_DIR, "dean_cataytay.png"), "rb") as f:
    SIG_JOIE = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

with open(os.path.join(SIG_DIR, "sheena_arcega.png"), "rb") as f:
    SIG_SHEENA = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

OFFICIAL_FACULTY_ROSTER = {
    "EE": {
        "full_time": [
            {"name": "Engr. Nikka Samantha A. Basan", "title": "Faculty Member", "username": "faculty_basan", "alias": "committee_basan", "roles": ["review_committee"]},
            {"name": "Engr. Charito O. Claro", "title": "Program Head - Electrical Engineering", "username": "faculty_claro", "alias": "programhead_claro", "roles": ["program_head", "review_committee"]},
            {"name": "Engr. Ramil Alvin B. Ramos", "title": "Faculty Member", "username": "faculty_ramos", "roles": ["review_committee"]},
            {"name": "Engr. Elwin Jay J. Tano", "title": "Faculty Member", "username": "faculty_tano", "roles": ["review_committee"]},
            {"name": "Engr. Donley Glenn Mabunga", "title": "Faculty Member", "username": "faculty_mabunga", "roles": ["review_committee"]},
        ],
        "part_time": [
            {"name": "Engr. Jayson P. Lolo", "title": "Part-Time Faculty Member", "username": "faculty_lolo", "roles": []},
        ]
    },
    "ECE": {
        "full_time": [
            {"name": "Engr. Delan Zoe H. Arenga", "title": "Faculty Member", "username": "faculty_arenga", "alias": "committee_arenga", "roles": ["review_committee"]},
            {"name": "Engr. Roberto I. Canda", "title": "Faculty Member", "username": "faculty_canda", "roles": ["review_committee"]},
            {"name": "Engr. Filmann T. Simpao", "title": "Faculty Member", "username": "faculty_simpao", "roles": ["review_committee"]},
            {"name": "Engr. Rosanna C. Ucat", "title": "Program Head - Electronics Engineering", "username": "faculty_ucat", "roles": ["program_head", "review_committee"]},
            {"name": "Engr. Kim P. Ravida", "title": "Faculty Member", "username": "faculty_ravida", "alias": "committee_ravida", "roles": ["review_committee"]},
            {"name": "Engr. Ernani Villasencio", "title": "Faculty Member", "username": "faculty_villasencio_e", "roles": ["review_committee"]},
        ],
        "part_time": [
            {"name": "Engr. Kim Andripa", "title": "Part-Time Faculty Member", "username": "faculty_andripa", "roles": []},
            {"name": "Engr. Cherry Vic O. Camposo", "title": "Part-Time Faculty Member", "username": "faculty_camposo", "roles": []},
            {"name": "Engr. Hans Marc C. Simplicio", "title": "Part-Time Faculty Member", "username": "faculty_simplicio", "roles": []},
        ]
    },
    "ME": {
        "full_time": [
            {"name": "Engr. Aquileo B. Estrera", "title": "Faculty Member", "username": "faculty_estrera", "roles": ["review_committee"]},
            {"name": "Engr. Christopher C. Gonzales", "title": "Faculty Member", "username": "faculty_gonzales", "roles": ["review_committee"]},
            {"name": "Engr. John Nerie L. Payao", "title": "Faculty Member", "username": "faculty_payao", "roles": ["review_committee"]},
            {"name": "Engr. Dennis G. Rebuta", "title": "Faculty Member", "username": "faculty_rebuta", "roles": ["review_committee"]},
            {"name": "Engr. Randy B. Tongson", "title": "Program Head - Mechanical Engineering", "username": "faculty_tongson", "roles": ["program_head", "review_committee"]},
        ],
        "part_time": [
            {"name": "Engr. Glemar O. Guarin", "title": "Part-Time Faculty Member", "username": "faculty_guarin", "roles": []},
        ]
    },
    "GE": {
        "full_time": [
            {"name": "Engr. Pherly Grace I. Bungao", "title": "Faculty Member", "username": "faculty_bungao", "roles": ["review_committee"]},
            {"name": "Engr. Kevin G. Cañada", "title": "Faculty Member", "username": "faculty_canada", "roles": ["review_committee"]},
            {"name": "Engr. Fillmore D. Masancay", "title": "Program Head - Geodetic Engineering", "username": "faculty_masancay", "roles": ["program_head", "review_committee"]},
        ],
        "part_time": [
            {"name": "Engr. Niron James Abas", "title": "Part-Time Faculty Member", "username": "faculty_abas", "roles": []},
        ]
    },
    "MinE": {
        "full_time": [
            {"name": "Engr. Norvein L. Calibo", "title": "Faculty Member", "username": "faculty_calibo", "roles": ["review_committee"]},
            {"name": "Engr. Mark John S. Pag-alaman", "title": "Program Head - Mining Engineering", "username": "faculty_pagalaman", "roles": ["program_head", "review_committee"]},
            {"name": "Engr. Elma Jane D. Rapal", "title": "Faculty Member", "username": "faculty_rapal", "roles": ["review_committee"]},
        ],
        "part_time": [
            {"name": "Engr. Lorel M. Castillo", "title": "Part-Time Faculty Member", "username": "faculty_castillo", "roles": []},
        ]
    },
    "BSGeo": {
        "full_time": [
            {"name": "Christian Paul F. Escarian", "title": "Faculty Member", "username": "faculty_escarian", "roles": ["review_committee"]},
            {"name": "Jerowen C. Licayan", "title": "Faculty Member", "username": "faculty_licayan", "roles": ["review_committee"]},
            {"name": "Marjorie T. Rebuyon", "title": "Faculty Member", "username": "faculty_rebuyon", "roles": ["review_committee"]},
            {"name": "Dean Lester P. Rejas", "title": "Program Head - Geology", "username": "faculty_rejas", "roles": ["program_head", "review_committee"]},
        ],
        "part_time": []
    },
    "CE": {
        "full_time": [
            {"name": "Engr. Bonifacio T. Aznar Jr.", "title": "Program Head - Civil Engineering", "username": "faculty_aznar", "roles": ["program_head", "review_committee"]},
            {"name": "Engr. Maria Cynthia Donita Caparida", "title": "Faculty Member", "username": "faculty_caparida", "roles": ["review_committee"]},
            {"name": "Engr. Ma. Dely P. Esberto", "title": "Faculty Member", "username": "faculty_esberto", "roles": ["review_committee"]},
            {"name": "Engr. Jeremias M. Lawas", "title": "Faculty Member", "username": "faculty_lawas", "roles": ["review_committee"]},
            {"name": "Engr. Reymar S. Ledesma", "title": "Faculty Member", "username": "faculty_ledesma", "roles": ["review_committee"]},
            {"name": "Engr. Eduardo S. Torrico Jr.", "title": "Faculty Member", "username": "faculty_torrico", "roles": ["review_committee"]},
            {"name": "Engr. Dalia M. Reconalla", "title": "Faculty Member", "username": "faculty_reconalla", "roles": ["review_committee"]},
        ],
        "part_time": [
            {"name": "Engr. Ernesto B. Lim Jr.", "title": "Part-Time Faculty Member", "username": "faculty_lim", "roles": []},
            {"name": "Engr. Florizel Ramas", "title": "Part-Time Faculty Member", "username": "faculty_ramas", "roles": []},
        ]
    },
    "SE": {
        "full_time": [
            {"name": "Engr. Sheena S. Arcega", "title": "Program Head - Sanitary Engineering", "username": "faculty_arcega", "roles": ["program_head", "review_committee"], "signature": SIG_SHEENA},
            {"name": "Engr. Rheanie R. Arnuco", "title": "Faculty Member", "username": "faculty_arnuco", "roles": ["review_committee"]},
            {"name": "Engr. Kathleen C. Cedeño", "title": "Faculty Member", "username": "faculty_cedeno", "roles": ["review_committee"]},
        ],
        "part_time": [
            {"name": "Engr. Jayvee Moore S. Dy", "title": "Part-Time Faculty Member", "username": "faculty_dy", "roles": []},
        ]
    },
    "ABE": {
        "full_time": [
            {"name": "Engr. Ryan M. Abenoja", "title": "Faculty Member", "username": "faculty_abenoja", "roles": ["review_committee"]},
            {"name": "Engr. Roland R. Bayron", "title": "Faculty Member", "username": "faculty_bayron", "roles": ["review_committee"]},
            {"name": "Engr. Ruben V. Cantones", "title": "Faculty Member", "username": "faculty_cantones", "roles": ["review_committee"]},
            {"name": "Engr. Joie D. Cataytay, Ph.D.", "title": "Dean, College of Engineering", "username": "dean_cataytay", "roles": ["dean", "review_committee"], "signature": SIG_JOIE},
            {"name": "Engr. Alona J. Che-Tangyie", "title": "Faculty Member", "username": "faculty_chetangyie", "roles": ["review_committee"]},
            {"name": "Engr. Sheila C. Cogay", "title": "Faculty Member", "username": "faculty_cogay", "roles": ["review_committee"]},
            {"name": "Engr. Honeybee S. Limbaro", "title": "Faculty Member", "username": "faculty_limbaro", "roles": ["review_committee"]},
            {"name": "Engr. Ronnie O. Lusares", "title": "Faculty Member", "username": "faculty_lusares", "roles": ["review_committee"]},
            {"name": "Engr. Roger C. Montepio, Ph.D.", "title": "Faculty Member", "username": "faculty_montepio", "roles": ["review_committee"]},
            {"name": "Engr. Renato C. Pareñas", "title": "Faculty Member", "username": "faculty_parenas", "roles": ["review_committee"]},
            {"name": "Engr. Teofilo Sevilla Jr.", "title": "Faculty Member", "username": "faculty_sevilla", "roles": ["review_committee"]},
            {"name": "Engr. Ruel Tuyogon", "title": "Program Head - Agricultural & Biosystems Engineering", "username": "faculty_tuyogon", "roles": ["program_head", "review_committee"]},
        ],
        "part_time": [
            {"name": "Engr. Kristine Faith Agato", "title": "Part-Time Faculty Member", "username": "faculty_agato", "roles": []},
            {"name": "Engr. Ireneo P. Amplayo", "title": "Part-Time Faculty Member", "username": "faculty_amplayo", "roles": []},
            {"name": "Engr. Irvin C. Generalao", "title": "Part-Time Faculty Member", "username": "faculty_generalao", "roles": []},
            {"name": "Engr. Filbert John Millan", "title": "Part-Time Faculty Member", "username": "faculty_millan", "roles": []},
            {"name": "Engr. Ben-Hur C. Rofosala", "title": "Part-Time Faculty Member", "username": "faculty_rofosala", "roles": []},
            {"name": "Engr. Aldrin I. Villacuer", "title": "Part-Time Faculty Member", "username": "faculty_villacuer", "roles": []},
        ]
    },
    "STAFF": {
        "full_time": [
            {"name": "Ayanekith L. Ababon", "title": "Technical Staff", "username": "staff_ababon", "roles": []},
            {"name": "Lemmor T. Benilan", "title": "Center Staff", "username": "staff_benilan", "roles": []},
            {"name": "Joyce Magdales", "title": "Technical Staff", "username": "staff_magdales", "roles": []},
            {"name": "Girlie Prevendido", "title": "Admin Aide IV", "username": "staff_prevendido", "roles": []},
            {"name": "Reynaldo Eltagonde Jr.", "title": "Laboratory Technician", "username": "staff_eltagonde", "roles": []},
            {"name": "Hans Marc C. Simplicio", "title": "Laboratory Technician", "username": "staff_simplicio_lab", "roles": []},
            {"name": "Maxwell A. Soller Jr.", "title": "Technical Staff", "username": "staff_soller", "roles": []},
        ],
        "part_time": []
    }
}


def sync_users_json():
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    else:
        users = {}

    default_pw_hash = generate_password_hash("password123")
    now_ts = datetime.now().isoformat(timespec="seconds")

    # Update faculty_tano
    if "faculty_tano" in users:
        users["faculty_tano"]["full_name"] = "Engr. Elwin Jay J. Tano"
        users["faculty_tano"]["position_title"] = "Faculty Member"

    # Update dean_cataytay
    if "dean_cataytay" in users:
        users["dean_cataytay"]["full_name"] = "Engr. Joie D. Cataytay, Ph.D."
        users["dean_cataytay"]["position_title"] = "Dean, College of Engineering"
        users["dean_cataytay"]["signature_data"] = SIG_JOIE

    # Sync all faculty
    for dept_code, groups in OFFICIAL_FACULTY_ROSTER.items():
        is_staff = (dept_code == "STAFF")
        all_members = groups.get("full_time", []) + groups.get("part_time", [])
        for fac in all_members:
            uname = fac["username"]
            target_unames = [uname]
            for u in target_unames:
                if u not in users:
                    users[u] = {
                        "full_name": fac["name"],
                        "role": "staff" if is_staff else "faculty",
                        "workflow_roles": fac.get("roles", []),
                        "position_title": fac["title"],
                        "program_codes": ["*"] if is_staff else [dept_code],
                        "college": "COLLEGE OF ENGINEERING",
                        "password_hash": default_pw_hash,
                        "must_change_password": False,
                        "created_at": now_ts,
                        "last_login": None,
                    }
                else:
                    users[u]["full_name"] = fac["name"]
                    users[u]["position_title"] = fac["title"]
                    users[u]["workflow_roles"] = fac.get("roles", users[u].get("workflow_roles", []))
                    users[u]["role"] = "staff" if is_staff else "faculty"
                    users[u]["program_codes"] = ["*"] if is_staff else [dept_code]

                if "signature" in fac:
                    users[u]["signature_data"] = fac["signature"]

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

    print(f"Users synced successfully! Total accounts: {len(users)}")


if __name__ == "__main__":
    sync_users_json()
