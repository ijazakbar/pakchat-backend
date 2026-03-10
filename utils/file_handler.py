# backend/utils/file_handler.py
import os
import uuid
import shutil
from typing import Dict, Any
import aiofiles
from fastapi import UploadFile
import PyPDF2
import pandas as pd
import docx
import json

class FileHandler:
    def __init__(self):
        self.upload_dir = "uploads"
        os.makedirs(self.upload_dir, exist_ok=True)
        
    async def save_file(self, file: UploadFile, user_id: str) -> Dict[str, Any]:
        """Save uploaded file"""
        # Generate unique filename
        file_id = str(uuid.uuid4())
        original_name = file.filename
        extension = os.path.splitext(original_name)[1]
        safe_name = f"{file_id}{extension}"
        file_path = os.path.join(self.upload_dir, safe_name)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        return {
            "id": file_id,
            "filename": original_name,
            "path": file_path,
            "size": file_size,
            "type": extension.lower()
        }
    
    async def extract_content(self, file_info: Dict[str, Any]) -> str:
        """Extract text content based on file type"""
        file_path = file_info["path"]
        file_type = file_info["type"]
        
        try:
            if file_type == '.pdf':
                return self._extract_pdf(file_path)
            elif file_type in ['.xlsx', '.xls', '.csv']:
                return self._extract_excel(file_path)
            elif file_type in ['.docx', '.doc']:
                return self._extract_word(file_path)
            elif file_type == '.json':
                return self._extract_json(file_path)
            elif file_type in ['.txt', '.md']:
                return self._extract_text(file_path)
            else:
                return f"Unsupported file type: {file_type}"
                
        except Exception as e:
            return f"Error extracting content: {str(e)}"
    
    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        text = []
        with open(file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            for page in pdf.pages:
                text.append(page.extract_text())
        return "\n".join(text)
    
    def _extract_excel(self, file_path: str) -> str:
        """Extract text from Excel/CSV"""
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        return df.to_string()
    
    def _extract_word(self, file_path: str) -> str:
        """Extract text from Word document"""
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    
    def _extract_json(self, file_path: str) -> str:
        """Extract text from JSON"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return json.dumps(data, indent=2)
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from text file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def delete_file(self, file_id: str):
        """Delete uploaded file"""
        # In production, also remove from database
        file_path = os.path.join(self.upload_dir, f"{file_id}.*")
        for f in os.listdir(self.upload_dir):
            if f.startswith(file_id):
                os.remove(os.path.join(self.upload_dir, f))