import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_drive_service():
    token_json = os.getenv("GOOGLE_TOKEN_JSON")

    if not token_json:
        raise RuntimeError("GOOGLE_TOKEN_JSON not found in environment variables")

    info = json.loads(token_json)
    creds = Credentials.from_authorized_user_info(info, SCOPES)

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("drive", "v3", credentials=creds)

def find_folder(service, folder_name, parent_id=None):
    query = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{folder_name}' and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    res = service.files().list(q=query, fields="files(id,name)").execute()
    items = res.get("files", [])
    return items[0]["id"] if items else None

def create_folder(service, folder_name, parent_id=None):
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]

def get_or_create_folder(service, folder_name, parent_id=None):
    folder_id = find_folder(service, folder_name, parent_id)
    return folder_id if folder_id else create_folder(service, folder_name, parent_id)

def upload_file(service, file_path, file_name, parent_folder_id):
    metadata = {
        "name": file_name,
        "parents": [parent_folder_id]
    }

    media = MediaFileUpload(file_path, resumable=False)

    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id,webViewLink"
    ).execute()

    return file["id"], file.get("webViewLink")

def upload_tab_files(root_folder_name, department, project, job_folder_name, tab_folder_name, files):
    service = get_drive_service()

    root_id = get_or_create_folder(service, root_folder_name)
    dept_id = get_or_create_folder(service, department, root_id)
    proj_id = get_or_create_folder(service, project, dept_id)
    job_id  = get_or_create_folder(service, job_folder_name, proj_id)
    tab_id  = get_or_create_folder(service, tab_folder_name, job_id)

    uploaded_files = []

    for f in files:
        file_id, link = upload_file(service, f["path"], f["name"], tab_id)
        uploaded_files.append({
            "file_name": f["name"],
            "file_id": file_id,
            "webViewLink": link
        })

    folder_url = f"https://drive.google.com/drive/folders/{tab_id}"
    return folder_url, uploaded_files
