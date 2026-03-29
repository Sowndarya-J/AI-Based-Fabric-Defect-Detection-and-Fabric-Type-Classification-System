import re
import hmac
import sqlite3
import hashlib
import secrets
import streamlit as st

DB_PATH = "users.db"

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@gmail\.com$")
UPPER_RE = re.compile(r"[A-Z]")
LOWER_RE = re.compile(r"[a-z]")
DIGIT_RE = re.compile(r"\d")
SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")

PBKDF2_ITERATIONS = 500_000
HASH_NAME = "sha256"
SALT_BYTES = 16

def sidebar_user_panel():
    import streamlit as st

    with st.sidebar:
        if st.session_state.get("user"):
            st.markdown(f"### 👤 {st.session_state.get('user')}")
        if st.session_state.get("role"):
            st.caption(f"Role: {st.session_state.get('role')}")
        if st.session_state.get("email"):
            st.caption(f"Email: {st.session_state.get('email')}")


def ensure_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "email" not in st.session_state:
        st.session_state.email = None


def generate_salt() -> str:
    return secrets.token_hex(SALT_BYTES)


def hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )
    return dk.hex()


def verify_password(password: str, salt_hex: str, stored_hash: str) -> bool:
    calc_hash = hash_password(password, salt_hex)
    return hmac.compare_digest(calc_hash, stored_hash)


def get_columns(cur, table_name="users"):
    cur.execute(f"PRAGMA table_info({table_name})")
    rows = cur.fetchall()
    return [row[1] for row in rows]


def init_user_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'operator'
        )
    """)
    con.commit()

    cols = get_columns(cur, "users")

    if "email" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "password_hash" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "salt" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN salt TEXT")
    if "created_at" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN created_at TEXT")

    con.commit()

    cur.execute("""
        UPDATE users
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL OR created_at = ''
    """)
    con.commit()

    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    except Exception:
        pass

    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    except Exception:
        pass

    con.commit()

    cur.execute("SELECT id, username, email, password_hash, salt FROM users WHERE username = ?", ("admin",))
    admin_row = cur.fetchone()

    if admin_row is None:
        salt = generate_salt()
        pw_hash = hash_password("Admin@123", salt)
        cols = get_columns(cur, "users")

        if "password" in cols:
            cur.execute("""
                INSERT INTO users (username, email, password, password_hash, salt, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("admin", "admin@gmail.com", pw_hash, pw_hash, salt, "admin"))
        else:
            cur.execute("""
                INSERT INTO users (username, email, password_hash, salt, role, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("admin", "admin@gmail.com", pw_hash, salt, "admin"))
    else:
        user_id, username_db, email_db, password_hash_db, salt_db = admin_row
        cols = get_columns(cur, "users")

        if not email_db:
            cur.execute("UPDATE users SET email = ? WHERE id = ?", ("admin@gmail.com", user_id))

        if not salt_db:
            salt_db = generate_salt()
            cur.execute("UPDATE users SET salt = ? WHERE id = ?", (salt_db, user_id))

        if not password_hash_db:
            password_hash_db = hash_password("Admin@123", salt_db)
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash_db, user_id))

        if "password" in cols:
            cur.execute("SELECT password FROM users WHERE id = ?", (user_id,))
            pwd_row = cur.fetchone()
            if pwd_row and (pwd_row[0] is None or str(pwd_row[0]).strip() == ""):
                cur.execute("UPDATE users SET password = ? WHERE id = ?", (password_hash_db, user_id))

    con.commit()
    con.close()


def validate_email(email: str):
    email = email.strip().lower()
    if not email:
        return False, "Email is required."
    if not EMAIL_REGEX.match(email):
        return False, "Use a valid Gmail address ending with @gmail.com."
    return True, ""


def validate_password(password: str):
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not UPPER_RE.search(password):
        return False, "Password must contain at least 1 uppercase letter."
    if not LOWER_RE.search(password):
        return False, "Password must contain at least 1 lowercase letter."
    if not DIGIT_RE.search(password):
        return False, "Password must contain at least 1 number."
    if not SPECIAL_RE.search(password):
        return False, "Password must contain at least 1 special character."
    return True, ""


def validate_username(username: str):
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    return True, ""


def register_user(username: str, email: str, password: str, role: str = "operator"):
    username = username.strip()
    email = email.strip().lower()

    ok, msg = validate_username(username)
    if not ok:
        return False, msg

    ok, msg = validate_email(email)
    if not ok:
        return False, msg

    ok, msg = validate_password(password)
    if not ok:
        return False, msg

    con = None
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            con.close()
            return False, "Username already exists."

        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            con.close()
            return False, "Email already exists."

        salt = generate_salt()
        pw_hash = hash_password(password, salt)

        cols = get_columns(cur, "users")

        if "password" in cols:
            cur.execute("""
                INSERT INTO users (username, email, password, password_hash, salt, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (username, email, pw_hash, pw_hash, salt, role))
        else:
            cur.execute("""
                INSERT INTO users (username, email, password_hash, salt, role, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (username, email, pw_hash, salt, role))

        con.commit()
        con.close()
        return True, "Registered successfully."

    except sqlite3.IntegrityError as e:
        if con:
            con.close()
        return False, f"Database integrity error: {e}"

    except Exception as e:
        if con:
            con.close()
        return False, f"Registration failed: {e}"


def check_login(email: str, password: str):
    email = email.strip().lower()

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cols = get_columns(cur, "users")

    if "password_hash" in cols and "salt" in cols:
        cur.execute("""
            SELECT username, email, password_hash, salt, role
            FROM users
            WHERE email = ?
        """, (email,))
        row = cur.fetchone()

        if row:
            username, email_db, password_hash_db, salt_db, role = row
            if password_hash_db and salt_db and verify_password(password, salt_db, password_hash_db):
                con.close()
                return True, username, role

    if "password" in cols:
        cur.execute("""
            SELECT username, role
            FROM users
            WHERE email = ? AND password = ?
        """, (email, password))
        row = cur.fetchone()
        if row:
            username, role = row
            con.close()
            return True, username, role

    con.close()
    return False, None, None


def get_all_users():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cols = get_columns(cur, "users")
    selected_cols = ["id", "username"]

    if "email" in cols:
        selected_cols.append("email")
    if "role" in cols:
        selected_cols.append("role")
    if "created_at" in cols:
        selected_cols.append("created_at")

    cur.execute(f"SELECT {', '.join(selected_cols)} FROM users ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    return rows


def require_login():
    ensure_session()
    if not st.session_state.get("logged_in", False):
        st.warning("Please login first.")
        st.stop()


def require_admin():
    require_login()
    if st.session_state.get("role") != "admin":
        st.error("Only admin can access this page.")
        st.stop()


def sidebar_user_panel():
    with st.sidebar:
        if st.session_state.get("user"):
            st.markdown(f"### 👤 {st.session_state.get('user')}")
        if st.session_state.get("role"):
            st.caption(f"Role: {st.session_state.get('role')}")
        if st.session_state.get("email"):
            st.caption(f"Email: {st.session_state.get('email')}")