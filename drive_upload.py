import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_drive_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise RuntimeError("Missing GOOGLE_CREDENTIALS_JSON env var for Drive")

    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def find_folder(service, folder_name, parent_id=None):
    q = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{folder_name}' and trashed=false"
    )
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = service.files().list(q=q, fields="files(id,name)").execute()
    items = res.get("files", [])
    return items[0]["id"] if items else None

def create_folder(service, folder_name, parent_id=None):
    meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]

def get_or_create_folder(service, folder_name, parent_id=None):
    fid = find_folder(service, folder_name, parent_id)
    return fid if fid else create_folder(service, folder_name, parent_id)

def upload_file(service, file_path, file_name, parent_folder_id):
    meta = {"name": file_name, "parents": [parent_folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    up = service.files().create(body=meta, media_body=media, fields="id,webViewLink").execute()
    return up["id"], up.get("webViewLink")

def upload_tab_files(root_folder_name, department, project, job_folder_name, tab_folder_name, files):
    service = get_drive_service()

    root_id = get_or_create_folder(service, root_folder_name)
    dept_id = get_or_create_folder(service, department, root_id)
    proj_id = get_or_create_folder(service, project, dept_id)
    job_id  = get_or_create_folder(service, job_folder_name, proj_id)
    tab_id  = get_or_create_folder(service, tab_folder_name, job_id)

    uploaded = []
    for f in files:
        file_id, link = upload_file(service, f["path"], f["name"], tab_id)
        uploaded.append({"file_name": f["name"], "file_id": file_id, "webViewLink": link})

    tab_folder_url = f"https://drive.google.com/drive/folders/{tab_id}"
    return tab_folder_url, uploaded
