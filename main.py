import os
import re
import json
import uuid
import tempfile
import shutil
from datetime import date
from typing import Any

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
    insert_job_tab,
)

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
DASHBOARD_TAB = os.getenv("DASHBOARD_TAB_NAME", "Dashboard")
DRIVE_ROOT = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER", "LaserCosting")

app = FastAPI()

# Dev-friendly CORS (works for localhost + future deployments)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://laser-cost-frontend-11fo.vercel.app",
    ],
    allow_credentials=False,
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

def normalize_material(material: str) -> str:
    m = (material or "").strip().lower()

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

def thickness_label_for_sheet(thk_mm: float) -> str:
    allowed = [
        0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0,
        4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0
    ]
    nearest = min(allowed, key=lambda x: abs(x - thk_mm))
    if nearest == 20.0:
        return "20mm"
    return f"{nearest:.1f} mm"

def _read_uploads_to_map(files: list[UploadFile]) -> dict[str, UploadFile]:
    # case-insensitive filename mapping
    return {f.filename.lower(): f for f in files if f and f.filename}

# ---------------------------------------------------
# Routes
# ---------------------------------------------------

@app.get("/")
def home():
    return {"status": "Internal Laser Cost Backend Running"}

# -------------------------
# PREVIEW (FAST) - No Drive, No DB
# -------------------------
@app.post("/preview")
async def preview(
    payload_json: str = Form(...),
    files: list[UploadFile] = File([])
):
    if not SPREADSHEET_ID:
        raise HTTPException(status_code=500, detail="SPREADSHEET_ID missing in environment variables")

    try:
        payload = json.loads(payload_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload_json: {e}")

    employee_email = (payload.get("employee_email") or "").strip()
    department = (payload.get("department") or "").strip()
    project = (payload.get("project") or "").strip()
    tabs = payload.get("tabs", [])

    if not employee_email or not department or not project:
        raise HTTPException(status_code=400, detail="Missing employee_email/department/project")

    if not isinstance(tabs, list) or not tabs:
        raise HTTPException(status_code=400, detail="Tabs required")

    upload_map = _read_uploads_to_map(files)
    temp_dir = tempfile.mkdtemp(prefix="laser_preview_")

    try:
        tab_results: list[dict[str, Any]] = []
        grand_total = 0.0

        # just a label; not uploading here
        preview_job_folder = f"{date.today().isoformat()}_PREVIEW"

        for t in tabs:
            material_input = (t.get("material") or "").strip()
            thickness_mm = float(t.get("thickness") or 0)
            tab_files = t.get("files", [])

            if not material_input or thickness_mm <= 0 or not tab_files:
                raise HTTPException(status_code=400, detail="Invalid tab data")

            material_sheet = normalize_material(material_input)
            thickness_sheet = thickness_label_for_sheet(thickness_mm)
            gas = gas_for_thickness(thickness_mm)

            total_cut_mm = 0.0
            total_area_mm2 = 0.0
            total_qty = 0

            # We'll return this to use later in submit
            file_manifest: list[dict[str, Any]] = []

            for item in tab_files:
                fname = (item.get("filename") or "").strip()
                qty = int(item.get("qty") or 0)

                if not fname or qty <= 0:
                    raise HTTPException(status_code=400, detail=f"Invalid file entry in tab: {item}")

                up = upload_map.get(fname.lower())
                if not up:
                    raise HTTPException(status_code=400, detail=f"File not uploaded: {fname}")

                local_path = os.path.join(temp_dir, up.filename)

                with open(local_path, "wb") as out:
                    shutil.copyfileobj(up.file, out)

                cut_len_mm, area_mm2 = calculate_dxf_metrics(local_path)

                total_cut_mm += cut_len_mm * qty
                total_area_mm2 += area_mm2 * qty
                total_qty += qty

                file_manifest.append({"filename": up.filename, "qty": qty})

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
                "pro_hours": 0,
            }

            cost_text = calculate_cost(SPREADSHEET_ID, DASHBOARD_TAB, sheet_inputs)
            cost_numeric = parse_cost_numeric(cost_text)

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
                "files": file_manifest,          # ✅ important for submit uploads
                "drive_folder_url": None,        # will be filled on submit
            })

            grand_total += cost_numeric

        return {
            "employee_email": employee_email,
            "department": department,
            "project": project,
            "tabs": tab_results,
            "grand_total": round(grand_total, 2),
            "currency": "LKR",
            "preview_job_folder": preview_job_folder,
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# -------------------------
# SUBMIT (REAL) - Upload to Drive + Save Supabase
# -------------------------
@app.post("/submit")
async def submit(
    payload_json: str = Form(...),
    files: list[UploadFile] = File([])
):
    try:
        preview_result_json = json.loads(payload_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload_json: {e}")

    employee_email = (preview_result_json.get("employee_email") or "").strip()
    department_name = (preview_result_json.get("department") or "").strip()
    project_name = (preview_result_json.get("project") or "").strip()
    tabs = preview_result_json.get("tabs", [])
    grand_total = float(preview_result_json.get("grand_total") or 0)

    if not employee_email or not department_name or not project_name:
        raise HTTPException(status_code=400, detail="Missing required fields")

    if not isinstance(tabs, list) or not tabs:
        raise HTTPException(status_code=400, detail="No tabs to save")

    # DB lookup errors -> readable 400
    try:
        department_id = get_department_id_by_name(department_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        project_id = get_project_id_by_name(project_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Map uploaded files
    upload_map = _read_uploads_to_map(files)
    if not upload_map:
        raise HTTPException(status_code=400, detail="No files uploaded for submit")

    temp_dir = tempfile.mkdtemp(prefix="laser_submit_")

    try:
        # Create DB job first (fast)
        job_id = create_job(
            employee_email=employee_email,
            department_id=department_id,
            project_id=project_id,
            final_cost_lkr=grand_total,
            remarks="",
        )

        # Use a stable folder name (job id)
        job_folder_name = f"{date.today().isoformat()}_{job_id}"

        saved_tabs = []

        # Upload files + insert tab rows
        for t in tabs:
            material = t.get("material")
            thickness_mm = float(t.get("thickness_mm") or 0)
            gas = t.get("gas") or gas_for_thickness(thickness_mm)

            # these should exist from previewResult
            total_cut_len_mm = float(t.get("total_cut_len_mm") or 0)
            total_area_sqft = float(t.get("total_area_sqft") or 0)
            quantity = int(t.get("quantity") or 0)
            cost_text = t.get("cost_text") or "0"
            cost_numeric = float(t.get("cost_numeric") or 0)

            file_manifest = t.get("files") or []
            if not file_manifest:
                raise HTTPException(status_code=400, detail="Submit payload missing tab files list. Please Preview again.")

            tab_folder_name = safe_tab_folder_name(material, thickness_mm)

            # Prepare local copies of uploaded files (for Drive upload)
            files_to_upload = []

            for item in file_manifest:
                fname = (item.get("filename") or "").strip()
                if not fname:
                    continue

                up = upload_map.get(fname.lower())
                if not up:
                    raise HTTPException(status_code=400, detail=f"File not uploaded in submit: {fname}")

                local_path = os.path.join(temp_dir, up.filename)
                with open(local_path, "wb") as out:
                    shutil.copyfileobj(up.file, out)

                files_to_upload.append({"path": local_path, "name": up.filename})

            # ✅ Upload to Drive here (not in preview)
            drive_folder_url, _ = upload_tab_files(
                root_folder_name=DRIVE_ROOT,
                department=department_name,
                project=project_name,
                job_folder_name=job_folder_name,
                tab_folder_name=tab_folder_name,
                files=files_to_upload,
            )

            # Save tab to DB
            tab_id = insert_job_tab(
                job_id=job_id,
                material=material,
                thickness_mm=thickness_mm,
                gas=gas,
                total_cut_len_mm=total_cut_len_mm,
                total_area_sqft=total_area_sqft,
                quantity=quantity,
                cost_text=cost_text,
                cost_numeric=cost_numeric,
                drive_folder_url=drive_folder_url,
            )

            saved_tabs.append({"tab_id": tab_id, "material": material, "drive_folder_url": drive_folder_url})

        return {
            "job_id": job_id,
            "saved_tabs": saved_tabs,
            "grand_total": grand_total,
            "currency": "LKR",
            "job_folder_name": job_folder_name,
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
