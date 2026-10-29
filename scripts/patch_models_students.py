with open('models.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_block = """        students = [
            StudentRecord(**{k: v for k, v in st.items() if k in StudentRecord.__dataclass_fields__})
            for st in data.get("students", [])
        ]"""

new_block = """        students = []
        for st in data.get("students", []):
            st_dict = {k: v for k, v in st.items() if k in StudentRecord.__dataclass_fields__}
            if not st_dict.get("last_name"):
                name = st.get("name", "")
                parts = [p.strip() for p in name.split(",", 1)]
                st_dict["last_name"] = parts[0] if parts and parts[0] else "Student"
                st_dict["first_name"] = parts[1] if len(parts) > 1 else ""
            if "first_name" not in st_dict:
                st_dict["first_name"] = ""
            students.append(StudentRecord(**st_dict))"""

if old_block in text:
    text = text.replace(old_block, new_block, 1)
    with open('models.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Updated StudentRecord parsing in models.py')
else:
    print('Old block not found!')
