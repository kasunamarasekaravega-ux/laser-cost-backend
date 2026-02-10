import os
import re
import json
import tempfile
import shutil
from datetime import date

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from dxf_calc import calculate_dxf_metrics
from sheets_calc import calculate_cost
from drive_upload import upload_tab_files
from db import (
    get_department_id_by_name,
    get_project_id_by_name,
    create_job,
    insert_job_tab
)

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
DASHBOARD_TAB  = os.getenv("DASHBOARD_TAB_NAME", "Dashboard")
DRIVE_ROOT     = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER", "LaserCosting")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,   # ✅ CHANGE THIS
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# Helper Functions
# ---------------------------------------------------

def gas_for_thickness(thk_mm: float) -> str:
    return "Com Air" if thk_mm <= 3.0 else "Oxygen"

def parse_cost_numeric(cost_str: str) -> float:
    if not cost_str:
        return 0.0
    matches = re.findall(r"[-+]?\d*\.\d+|\d+", str(cost_str).replace(",", ""))
    if not matches:
        return 0.0
    return float(matches[0])

def safe_tab_folder_name(material: str, thickness_mm: float) -> str:
    thk = f"{thickness_mm:.1f}".rstrip("0").rstrip(".")
    return f"{material}_{thk}"

# Map shortcuts to sheet dropdown names
def normalize_material(material: str) -> str:
    m = material.strip().lower()

    mapping = {
        "ms": "Mild Steel",
        "mild steel": "Mild Steel",

        "ss": "Stainless Steel (SS)",
        "stainless": "Stainless Steel (SS)",
        "stainless steel": "Stainless Steel (SS)",

        "al": "Aluminium",
        "alu": "Aluminium",
        "aluminium": "Aluminium",

        "copper": "Copper",
        "silicon steel": "Silicon steel",
        "zinc-coated steel": "Zinc-Coated Steel",
        "gi": "Zinc-Coated Steel",
    }

    return mapping.get(m, material)

# Thickness formatting must match your sheet dropdown exactly:
# "0.5 mm", "1.0 mm", ..., "15.0 mm", and "20mm"
def thickness_label_for_sheet(thk_mm: float) -> str:
    allowed = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0,
               4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0]

    nearest = min(allowed, key=lambda x: abs(x - thk_mm))

    if nearest == 20.0:
        return "20mm"
    else:
        return f"{nearest:.1f} mm"

# ---------------------------------------------------
# Routes
# ---------------------------------------------------

@app.get("/")
def home():
    return {"status": "Internal Laser Cost Backend Running"}

# -------------------------
# PREVIEW (Calculate only)
# -------------------------
@app.post("/preview")
async def preview(
    payload_json: str = Form(...),
    files: list[UploadFile] = File([])
):
    if not SPREADSHEET_ID:
        raise HTTPException(status_code=500, detail="SPREADSHEET_ID missing in .env")

    try:
        payload = json.loads(payload_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload_json: {e}")

    employee_email = payload.get("employee_email", "").strip()
    department = payload.get("department", "").strip()
    project = payload.get("project", "").strip()
    tabs = payload.get("tabs", [])

    if not employee_email or not department or not project:
        raise HTTPException(status_code=400, detail="Missing employee_email/department/project")

    if not isinstance(tabs, list) or len(tabs) == 0:
        raise HTTPException(status_code=400, detail="Tabs required")

    upload_map = {f.filename.lower(): f for f in files if f and f.filename}

    temp_dir = tempfile.mkdtemp(prefix="laser_job_")

    try:
        tab_results = []
        grand_total = 0.0

        preview_job_folder = f"{date.today().isoformat()}_PREVIEW"

        for t in tabs:
            material_input = t.get("material", "")
            thickness_mm = float(t.get("thickness", 0))
            tab_files = t.get("files", [])

            if not material_input or thickness_mm <= 0 or not tab_files:
                raise HTTPException(status_code=400, detail="Invalid tab data")

            material_sheet = normalize_material(material_input)
            thickness_sheet = thickness_label_for_sheet(thickness_mm)
            gas = gas_for_thickness(thickness_mm)

            total_cut_mm = 0.0
            total_area_mm2 = 0.0
            total_qty = 0

            files_to_upload = []

            for item in tab_files:
                fname = item.get("filename", "").strip()
                qty = int(item.get("qty", 0))

                if fname.lower() not in upload_map:
                    raise HTTPException(status_code=400, detail=f"File not uploaded: {fname}")

                up = upload_map[fname.lower()]
                local_path = os.path.join(temp_dir, up.filename)

                with open(local_path, "wb") as out:
                    shutil.copyfileobj(up.file, out)

                cut_len_mm, area_mm2 = calculate_dxf_metrics(local_path)

                total_cut_mm += cut_len_mm * qty
                total_area_mm2 += area_mm2 * qty
                total_qty += qty

                files_to_upload.append({"path": local_path, "name": up.filename})

            total_area_sqft = total_area_mm2 * 0.0000107639

            sheet_inputs = {
                "material": material_sheet,
                "thickness": thickness_sheet,
                "gas": gas,
                "area_sqft": round(total_area_sqft, 4),
                "cut_len": round(total_cut_mm, 2),
                "bends": 0,
                "number_of_pieces": 1,
                "fab_hours": 0,
                "pro_hours": 0
            }

            cost_text = calculate_cost(SPREADSHEET_ID, DASHBOARD_TAB, sheet_inputs)
            cost_numeric = parse_cost_numeric(cost_text)

            tab_folder_name = safe_tab_folder_name(material_sheet, thickness_mm)

            drive_folder_url, _ = upload_tab_files(
                root_folder_name=DRIVE_ROOT,
                department=department,
                project=project,
                job_folder_name=preview_job_folder,
                tab_folder_name=tab_folder_name,
                files=files_to_upload
            )

            tab_results.append({
                "material": material_sheet,
                "thickness_mm": thickness_mm,
                "thickness_sheet": thickness_sheet,
                "gas": gas,
                "total_cut_len_mm": round(total_cut_mm, 2),
                "total_area_sqft": round(total_area_sqft, 4),
                "quantity": total_qty,
                "cost_text": cost_text,
                "cost_numeric": cost_numeric,
                "drive_folder_url": drive_folder_url
            })

            grand_total += cost_numeric

        return {
            "employee_email": employee_email,
            "department": department,
            "project": project,
            "tabs": tab_results,
            "grand_total": round(grand_total, 2),
            "currency": "LKR",
            "preview_job_folder": preview_job_folder
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# -------------------------
# SUBMIT (Save to DB)
# -------------------------
@app.post("/submit")
def submit(preview_result_json: dict):

    employee_email = preview_result_json.get("employee_email", "").strip()
    department_name = preview_result_json.get("department", "").strip()
    project_name = preview_result_json.get("project", "").strip()
    tabs = preview_result_json.get("tabs", [])
    grand_total = float(preview_result_json.get("grand_total", 0))

    if not employee_email or not department_name or not project_name:
        raise HTTPException(status_code=400, detail="Missing required fields")

    if not tabs:
        raise HTTPException(status_code=400, detail="No tabs to save")

    # Lookup IDs
    department_id = get_department_id_by_name(department_name)
    project_id = get_project_id_by_name(project_name)

    # Create job
    job_id = create_job(
        employee_email=employee_email,
        department_id=department_id,
        project_id=project_id,
        final_cost_lkr=grand_total,
        remarks=""
    )

    saved_tabs = []

    for t in tabs:
        tab_id = insert_job_tab(
            job_id=job_id,
            material=t["material"],
            thickness_mm=t["thickness_mm"],
            gas=t["gas"],
            total_cut_len_mm=t["total_cut_len_mm"],
            total_area_sqft=t["total_area_sqft"],
            quantity=t["quantity"],
            cost_text=t["cost_text"],
            cost_numeric=t["cost_numeric"],
            drive_folder_url=t["drive_folder_url"]
        )

        saved_tabs.append({
            "tab_id": tab_id,
            "material": t["material"]
        })

    return {
        "job_id": job_id,
        "saved_tabs": saved_tabs,
        "grand_total": grand_total,
        "currency": "LKR"
    }
