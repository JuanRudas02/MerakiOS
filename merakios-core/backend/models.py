from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON, Column
from sqlalchemy import CheckConstraint
from pgvector.sqlalchemy import Vector
from enum import Enum
import uuid
from datetime import datetime

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    AUDITED = "audited"
    DESIGNING = "designing"
    COMPLETED = "completed"

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str

class Project(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    name: str
    niche: str
    status: ProjectStatus = Field(default=ProjectStatus.DRAFT)
    
    # JSONB columns for agent outputs (Shared State)
    audit_data: Optional[dict] = Field(default=None, sa_column=Column(JSON)) # Genesis Output
    search_results: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON)) # Genesis Raw Data
    funnel_structure: Optional[dict] = Field(default=None, sa_column=Column(JSON)) # Blueprint Output
    
    # Director / Live Data
    live_metrics: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    alert_history: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))
    
    # pgvector embedding for project description/memory
    # Vector dimension 1536 is standard for OpenAI embeddings
    embedding: Optional[List[float]] = Field(default=None, sa_column=Column(Vector(1536)))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
