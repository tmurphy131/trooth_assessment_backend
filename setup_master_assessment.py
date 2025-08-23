"""
Script to create the Master Trooth Assessment with all questions from assessment_info.md
"""
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from app.db import engine, SessionLocal
from app.models import *
import uuid

def create_master_trooth_assessment():
    """Create the master Trooth Assessment"""
    
    # Connect to database
    with engine.begin() as conn:
        # Check if Trooth Assessment already exists
        result = conn.execute(text("""
            SELECT id FROM assessment_templates 
            WHERE is_master_assessment = TRUE
        """))
        existing = result.fetchone()
        
        if existing:
            print("⚠️  Master Trooth Assessment already exists")
            return existing[0]
        
        # Create the master Trooth Assessment
        trooth_assessment_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO assessment_templates (id, name, description, is_published, is_master_assessment, created_at)
            VALUES (:id, :name, :description, :is_published, :is_master_assessment, NOW())
        """), {
            "id": trooth_assessment_id,
            "name": "Master Trooth Assessment",
            "description": "The official comprehensive spiritual assessment for all apprentices. Covers 7 key areas: Spiritual Growth, Prayer Life, Bible Study, Community & Fellowship, Service & Ministry, Discipleship, and Faith Practice.",
            "is_published": True,
            "is_master_assessment": True
        })
        
        print("✅ Created Master Trooth Assessment")
        return trooth_assessment_id

if __name__ == "__main__":
    result = create_master_trooth_assessment()
    print(f"Master Assessment ID: {result}")
