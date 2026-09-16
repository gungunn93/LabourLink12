import os
import uuid
from flask import Blueprint, request, send_from_directory, current_app
from flask_jwt_extended import jwt_required
from utils.responses import ok, err

uploads_bp = Blueprint("uploads", __name__)


@uploads_bp.post("/upload")
@jwt_required()
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return err("No file uploaded")
    allowed = {"png", "jpg", "jpeg", "webp", "pdf"}
    if "." not in file.filename:
        return err("File extension is required")
    extension = file.filename.rsplit(".", 1)[1].lower()
    if extension not in allowed:
        return err("Unsupported file type")
    filename = f"{uuid.uuid4().hex}.{extension}"
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    return ok({"filename": filename, "url": f"/uploads/{filename}"}, "File uploaded")
