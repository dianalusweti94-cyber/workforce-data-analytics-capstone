"""
Roblox Africa Operations - Workforce Analytics Capstone
Cleaning + MySQL load script

Run this once to: clean all 7 datasets (applying the Client Email's confirmed
fixes plus duplicates found during review), then load them straight into
MySQL - no Import Wizard involved.

Before running:
  pip install pandas openpyxl sqlalchemy pymysql --break-system-packages
  Fill in your MySQL connection details in the CONFIG section below.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import String, Integer
from urllib.parse import quote_plus

# ── CONFIG ────────────────────────────────────────────────────────────────
MYSQL_USER = "root"
MYSQL_PASSWORD = "your_password_here"
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_DB = "roblox_workforce_db"          # will be created if it doesn't exist
DATA_DIR = "."                             # folder holding the 7 .xlsx files

# Encode the password so special characters (like @) don't break the
# connection string - MySQL passwords with @, :, / etc. need this.
MYSQL_PASSWORD_ENCODED = quote_plus(MYSQL_PASSWORD)

# ── 1. LOAD RAW DATASETS ────────────────────────────────────────────────
employee = pd.read_excel(f"{DATA_DIR}/employee_dataset.xlsx")
department = pd.read_excel(f"{DATA_DIR}/Department.xlsx")
education = pd.read_excel(f"{DATA_DIR}/Education.xlsx")
finance = pd.read_excel(f"{DATA_DIR}/finance_dataset.xlsx")
emp_performance = pd.read_excel(f"{DATA_DIR}/employee_performance.xlsx")
health = pd.read_excel(f"{DATA_DIR}/health_dataset.xlsx")
dept_performance = pd.read_excel(f"{DATA_DIR}/department_performance.xlsx")

print("Raw row counts:")
for name, df in [("employee", employee), ("department", department),
                  ("education", education), ("finance", finance),
                  ("emp_performance", emp_performance), ("health", health),
                  ("dept_performance", dept_performance)]:
    print(f"  {name}: {len(df)}")

# ── 2. CLEAN EMPLOYEE DATASET ────────────────────────────────────────────
# 2a. Drop exact duplicate rows (4 EmployeeIDs each appeared twice, identical)
before = len(employee)
employee = employee.drop_duplicates(subset="EmployeeID", keep="first").copy()
print(f"\nEmployee: dropped {before - len(employee)} duplicate rows")

# 2b. Age fixes (client email: IDs 279 and 21187)
employee.loc[employee.EmployeeID == 279, "Age"] = 48
employee.loc[employee.EmployeeID == 21187, "Age"] = 30

# 2c. Gender fixes - 7 missing values -> Female, plus the "Femal" typo -> Female
missing_gender_ids = [4470, 5826, 9301, 12333, 19342, 25405, 26938]
employee.loc[employee.EmployeeID.isin(missing_gender_ids), "Gender"] = "Female"
employee.loc[employee.Gender == "Femal", "Gender"] = "Female"

# 2d. Missing Department Code (ID 25142 -> FIN)
employee.loc[employee.EmployeeID == 25142, "Department Code"] = "FIN"

# 2e. Missing Last Name (ID 28686 -> Campbell)
employee.loc[employee.EmployeeID == 28686, "Last Name"] = "Campbell"

# 2f. Missing phone numbers, mapped by EmployeeID (client email)
# Cast to object dtype first so we can assign string values into a
# column that started as float64 (source column has scientific notation)
employee["Phone Number"] = employee["Phone Number"].astype(object)
phone_fixes = {
    3257: "233590129809",
    14367: "233556780467",
    17803: "233500129809",
    17986: "233500012987",
    21281: "233260125678",
    23486: "233530895670",
    28940: "233540122309",
}
for emp_id, phone in phone_fixes.items():
    employee.loc[employee.EmployeeID == emp_id, "Phone Number"] = phone

# 2g. Missing employee_status -> Active
employee["employee_status"] = employee["employee_status"].fillna("Active")

# 2h. Standardize Phone Number to a clean string for every row
#     (source column is float64 with scientific notation; convert to plain digits)
def clean_phone(val):
    if pd.isna(val):
        return None
    if isinstance(val, str):
        return val
    return str(int(round(float(val))))

employee["Phone Number"] = employee["Phone Number"].apply(clean_phone)

# 2i. Convert Date Joined from Excel serial number to an actual date
employee["Date Joined"] = pd.to_datetime(
    employee["Date Joined"], unit="D", origin="1899-12-30"
).dt.date

# 2j. Sanity check - confirm no missing values remain in the columns we fixed
check_cols = ["Age", "Gender", "Department Code", "Last Name", "Phone Number", "employee_status"]
remaining_missing = employee[check_cols].isna().sum()
print("\nEmployee - remaining missing values after cleaning (should all be 0):")
print(remaining_missing)

# ── 3. CLEAN EDUCATION DATASET ───────────────────────────────────────────
before = len(education)
education = education.drop_duplicates(subset="employee_id", keep="first").copy()
print(f"\nEducation: dropped {before - len(education)} duplicate rows")

# ── 4. OTHER DATASETS ────────────────────────────────────────────────────
# Department, Finance, Employee Performance, Health, Department Performance
# came back clean on review - no missing values, no duplicates, keys all
# matched. No changes needed beyond loading them as-is.

# ── 5. LOAD EVERYTHING INTO MYSQL (no Import Wizard, all scripted) ──────
# Connect to the server first (no db yet) and rebuild the database fresh
# each run - this avoids errors from foreign keys added by a previous,
# partially-completed run of add_keys.sql blocking table drops/replaces.
server_engine = create_engine(f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD_ENCODED}@{MYSQL_HOST}:{MYSQL_PORT}")
with server_engine.connect() as conn:
    conn.execute(text(f"DROP DATABASE IF EXISTS {MYSQL_DB}"))
    conn.execute(text(f"CREATE DATABASE {MYSQL_DB}"))
    conn.commit()

engine = create_engine(
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD_ENCODED}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

tables = {
    "department": department,
    "employee": employee,
    "education": education,
    "health": health,
    "finance": finance,
    "employee_performance": emp_performance,
    "department_performance": dept_performance,
}

# Text columns that will be used as PRIMARY/FOREIGN keys need a sized
# VARCHAR type, not the generic TEXT type pandas creates by default -
# MySQL can't build a key on TEXT without specifying a length.
key_column_dtypes = {
    "department": {"department_code": String(10), "department_name": String(100)},
    "employee": {"Department Code": String(10)},
    "department_performance": {"Department": String(100)},
}

for table_name, df in tables.items():
    dtype = key_column_dtypes.get(table_name)
    df.to_sql(table_name, engine, if_exists="replace", index=False, dtype=dtype)
    print(f"Loaded '{table_name}' -> {len(df)} rows")

print("\nAll 7 tables cleaned and loaded into MySQL database:", MYSQL_DB)
print("Next step: add PRIMARY KEY / FOREIGN KEY constraints (see add_keys.sql)")
