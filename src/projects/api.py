from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{project_name}/thumbnail", response_class=HTMLResponse)
async def get_thumbnail_form(project_name: str):
    return (
        """
        <html>
          <head><title>Upload Thumbnail</title></head>
          <body>
            <h1>Upload thumbnail for project</h1>
            <form action="" method="post" enctype="multipart/form-data">
              <input type="file" name="file" accept="image/png,image/jpeg,image/webp" />
              <button type="submit">Upload</button>
            </form>
          </body>
        </html>
        """
    )


MAX_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("/{project_name}/thumbnail")
async def upload_thumbnail(project_name: str, file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Use PNG, JPEG, or WebP.")

    data = await file.read()
    size = len(data)
    if size > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Max 5 MB.")

    return JSONResponse(
        {
            "status": "ok",
            "project": project_name,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": size,
        }
    )
