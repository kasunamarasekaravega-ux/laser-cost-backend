import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

def get_conn():
    if not DB_URL:
        raise RuntimeError("SUPABASE_DB_URL missing in .env")
    return psycopg2.connect(DB_URL, sslmode="require")

def get_department_id_by_name(department_name: str) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("select id from departments where name = %s limit 1", (department_name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise ValueError(f"Department not found: {department_name}")
    return str(row[0])

def get_project_id_by_name(project_name: str) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("select id from projects where name = %s limit 1", (project_name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise ValueError(f"Project not found: {project_name}")
    return str(row[0])

def create_job(employee_email: str, department_id: str, project_id: str, final_cost_lkr: float, remarks: str = "") -> str:
    """
    Your jobs table columns:
    id, created_at, user_id, department_id, project_id, material, thickness, quantity,
    cut_length, pierce_count, final_cost_lkr, remarks, employee_email

    We will fill required fields with safe defaults to avoid constraint issues.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        insert into jobs (
            employee_email,
            department_id,
            project_id,
            final_cost_lkr,
            remarks,
            material,
            thickness,
            quantity,
            cut_length,
            pierce_count
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        returning id
    """, (
        employee_email,
        department_id,
        project_id,
        float(final_cost_lkr),
        remarks or "",
        "MIXED",     # job has multiple tabs, so keep as MIXED
        0,           # not meaningful at job level
        0,
        0,
        0
    ))

    job_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return str(job_id)

def insert_job_tab(
    job_id: str,
    material: str,
    thickness_mm: float,
    gas: str,
    total_cut_len_mm: float,
    total_area_sqft: float,
    quantity: int,
    cost_text: str,
    cost_numeric: float,
    drive_folder_url: str
) -> str:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        insert into job_tabs (
            job_id,
            material,
            thickness,
            gas,
            total_cut_len,
            total_area_sqft,
            quantity,
            cost_text,
            cost_numeric,
            drive_folder_url
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        returning id
    """, (
        job_id,
        material,
        float(thickness_mm),
        gas,
        float(total_cut_len_mm),
        float(total_area_sqft),
        int(quantity),
        cost_text,
        float(cost_numeric),
        drive_folder_url
    ))

    tab_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return str(tab_id)
