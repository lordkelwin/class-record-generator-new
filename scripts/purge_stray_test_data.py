import os
import json
import sqlite3
import shutil

DB_PATH = os.path.join("data", "academic_catalog.db")
STUDENTS_FILE = os.path.join("data", "students.json")
USERS_FILE = os.path.join("data", "users.json")
NOTIFS_FILE = os.path.join("data", "sent_notifications.json")
DELETED_USERS_FILE = os.path.join("data", "deleted_users.json")
COURSES_DIR = os.path.join("data", "courses")

VALID_COURSES = {"c_bb5266e73b", "c_3fcdbfc361", "c_3883ebffe9", "c_144aaf4901"}

TEST_STUDENT_IDS = {
    "TEST_ANTIGRAVITY_S01",
    "2026-88002",
    "2026-99001",
    "2026-99002",
    "2026-99003",
    "2026-99004",
    "2026-99005",
    "2026-NAV01",
    "2026-1001",
    "2026-9999",
    "2026-1006",
    "2026-1007",
    "2026-1008",
    "2026-99991",
    "2026-99992",
    "2024-99001",
    "2024-99002",
}

def purge_all_test_data():
    print(">>> Starting Full Audit & Permanent Test Data Purge...")

    # 1. Purge SQLite Database Tables
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1a. Purge test course_records
    placeholders = ",".join("?" for _ in VALID_COURSES)
    cur.execute(f"DELETE FROM course_records WHERE course_id NOT IN ({placeholders})", list(VALID_COURSES))
    print(f"Purged stray course_records. Remaining valid courses: {len(VALID_COURSES)}")

    # 1b. Purge child tables for removed courses
    child_tables = [
        "assessment_categories",
        "assessment_items",
        "student_course_grades",
        "syllabus_reviews_and_signatures",
        "syllabus_evaluations"
    ]
    for table in child_tables:
        cur.execute(f"DELETE FROM {table} WHERE course_id NOT IN ({placeholders})", list(VALID_COURSES))
        print(f"Purged stray rows in {table} referencing test courses.")

    # 1c. Purge test students from app_students
    st_placeholders = ",".join("?" for _ in TEST_STUDENT_IDS)
    cur.execute(f"DELETE FROM app_students WHERE student_id IN ({st_placeholders})", list(TEST_STUDENT_IDS))
    cur.execute("DELETE FROM app_students WHERE student_id LIKE 'TEST%' OR student_id LIKE '%test%' OR full_name LIKE '%Student, %'")
    print("Purged stray test students from app_students.")

    # 1d. Clean enrolled_courses and acknowledgments in remaining app_students
    rows = cur.execute("SELECT student_id, enrolled_courses, assessment_acknowledgments, syllabus_acknowledgments FROM app_students").fetchall()
    for sid, enrolled_raw, a_acks_raw, s_acks_raw in rows:
        try:
            enrolled = json.loads(enrolled_raw or "[]")
        except Exception:
            enrolled = []
        cleaned_enrolled = [c for c in enrolled if c in VALID_COURSES]

        try:
            a_acks = json.loads(a_acks_raw or "{}")
        except Exception:
            a_acks = {}
        cleaned_a_acks = {k: v for k, v in a_acks.items() if k in VALID_COURSES}

        try:
            s_acks = json.loads(s_acks_raw or "{}")
        except Exception:
            s_acks = {}
        cleaned_s_acks = {k: v for k, v in s_acks.items() if k in VALID_COURSES}

        cur.execute(
            "UPDATE app_students SET enrolled_courses = ?, assessment_acknowledgments = ?, syllabus_acknowledgments = ? WHERE student_id = ?",
            (json.dumps(cleaned_enrolled), json.dumps(cleaned_a_acks), json.dumps(cleaned_s_acks), sid)
        )
    print("Cleaned enrolled_courses references for all legitimate students in SQLite.")

    # 1e. Clean test users from app_users
    cur.execute("DELETE FROM app_users WHERE username LIKE 'test_%' OR username LIKE '%tester%'")
    conn.commit()
    conn.close()

    # 2. Purge data/students.json
    if os.path.exists(STUDENTS_FILE):
        with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
            sts = json.load(f)
        cleaned_sts = {}
        for sid, s in sts.items():
            name = s.get("full_name") or s.get("name") or ""
            if sid in TEST_STUDENT_IDS or "test" in sid.lower() or "test" in name.lower() or name.startswith("Student, "):
                continue
            enrolled = s.get("enrolled_courses") or []
            s["enrolled_courses"] = [c for c in enrolled if c in VALID_COURSES]
            if "assessment_acknowledgments" in s and isinstance(s["assessment_acknowledgments"], dict):
                s["assessment_acknowledgments"] = {k: v for k, v in s["assessment_acknowledgments"].items() if k in VALID_COURSES}
            if "syllabus_acknowledgments" in s and isinstance(s["syllabus_acknowledgments"], dict):
                s["syllabus_acknowledgments"] = {k: v for k, v in s["syllabus_acknowledgments"].items() if k in VALID_COURSES}
            cleaned_sts[sid] = s
        with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned_sts, f, indent=2, ensure_ascii=False)
        print(f"Cleaned students.json: retained {len(cleaned_sts)} official students.")

    # 3. Clean data/courses directory
    if os.path.exists(COURSES_DIR):
        for entry in os.listdir(COURSES_DIR):
            entry_path = os.path.join(COURSES_DIR, entry)
            if os.path.isdir(entry_path):
                # If directory name starts with test_ or is a test user, delete entire folder
                if entry.startswith("test_") or entry in ["default", "faculty_task2", "faculty_tester", "test_u"]:
                    shutil.rmtree(entry_path, ignore_errors=True)
                    print(f"Removed test courses directory: {entry}")
                else:
                    # Clean out files not in VALID_COURSES
                    for f in os.listdir(entry_path):
                        if f.endswith(".json"):
                            cid = os.path.splitext(f)[0]
                            if cid not in VALID_COURSES:
                                os.remove(os.path.join(entry_path, f))
                                print(f"Removed stray course file: {entry}/{f}")

    # 4. Clean data/sent_notifications.json
    if os.path.exists(NOTIFS_FILE):
        try:
            with open(NOTIFS_FILE, "r", encoding="utf-8") as f:
                notifs = json.load(f)
            cleaned_notifs = []
            for n in notifs:
                n_str = json.dumps(n).lower()
                if any(tok in n_str for tok in ["test", "nav", "c_1", "sample"]):
                    continue
                cleaned_notifs.append(n)
            with open(NOTIFS_FILE, "w", encoding="utf-8") as f:
                json.dump(cleaned_notifs, f, indent=2)
            print(f"Cleaned sent_notifications.json: retained {len(cleaned_notifs)} genuine notifications.")
        except Exception as e:
            print("Error cleaning notifications:", e)

    # 5. Clean data/deleted_users.json
    if os.path.exists(DELETED_USERS_FILE):
        try:
            with open(DELETED_USERS_FILE, "r", encoding="utf-8") as f:
                del_users = json.load(f)
            cleaned_del = [u for u in del_users if not u.startswith("test_") and u not in ["faculty_tester"]]
            with open(DELETED_USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(cleaned_del, f, indent=2)
            print(f"Cleaned deleted_users.json: retained {len(cleaned_del)} entries.")
        except Exception as e:
            print("Error cleaning deleted users:", e)

    # 6. Remove root 0-byte academic_catalog.db if present
    if os.path.exists("academic_catalog.db"):
        try:
            os.remove("academic_catalog.db")
            print("Removed extraneous root academic_catalog.db file.")
        except Exception:
            pass

    # 7. Also clean students array inside the valid courses' JSON and DB
    # to ensure no test students remain in blueprint['students'] of valid courses!
    for cid in VALID_COURSES:
        doc = None
        # Check SQLite
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        row = cur.execute("SELECT owner, blueprint_json FROM course_records WHERE course_id = ?", (cid,)).fetchone()
        if row:
            owner = row[0]
            try:
                bp = json.loads(row[1] or "{}")
                sts = bp.get("students") or []
                clean_sts = [s for s in sts if str(s.get("student_id") or "") not in TEST_STUDENT_IDS and not str(s.get("student_id") or "").startswith("TEST")]
                bp["students"] = clean_sts
                cur.execute("UPDATE course_records SET blueprint_json = ? WHERE course_id = ?", (json.dumps(bp), cid))
                conn.commit()

                # Also update JSON file on disk
                fp = os.path.join(COURSES_DIR, owner, f"{cid}.json")
                if os.path.exists(fp):
                    with open(fp, "r", encoding="utf-8") as f:
                        jdoc = json.load(f)
                    jbp = jdoc.get("blueprint") or {}
                    jbp["students"] = clean_sts
                    jdoc["blueprint"] = jbp
                    with open(fp, "w", encoding="utf-8") as f:
                        json.dump(jdoc, f, indent=2)
            except Exception as e:
                print(f"Error cleaning students in {cid}:", e)
        conn.close()

    print(">>> Permanent Test Data Purge Complete!")

if __name__ == "__main__":
    purge_all_test_data()
