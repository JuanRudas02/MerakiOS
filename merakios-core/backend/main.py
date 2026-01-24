from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Optional
from pydantic import BaseModel
import uuid

# Local imports
from database import init_db, get_session
from models import Project, ProjectStatus
from agents.genesis import genesis_app
from agents.blueprint import blueprint_app

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MerakiOS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"], # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.security import OAuth2PasswordRequestForm
from auth import verify_password, create_access_token, get_current_user
from models import User

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    statement = select(User).where(User.email == form_data.username)
    result = await session.execute(statement)
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": {"email": user.email, "id": user.id}}

@app.on_event("startup")
async def on_startup():
    await init_db()

# --- DTOs ---
class ProjectCreate(BaseModel):
    name: str
    niche: str
    user_id: uuid.UUID  # Simplified for demo (normally via auth token)

class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    niche: str
    status: ProjectStatus
    audit_data: Optional[dict]
    funnel_structure: Optional[dict]

# --- Background Tasks ---
async def run_genesis_agent(project_id: uuid.UUID, session_factory):
    """
    Background task to run Genesis Agent and update DB.
    We create a new session here because the request session will be closed.
    """
    from database import get_session # Re-import generator to manually use it or use sessionmaker directly
    from database import engine
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            return

        project.status = ProjectStatus.ANALYZING
        await session.commit()
        
        # Invoke Genesis Agent
        initial_state = {"niche": project.niche, "url": None}
        result = await genesis_app.ainvoke(initial_state)
        
        final_report = result.get("final_report", {})
        
        # Update Project
        project.audit_data = final_report
        project.status = ProjectStatus.AUDITED
        session.add(project)
        await session.commit()
        print(f"--- GENESIS COMPLETE FOR PROJECT {project_id} ---")

async def run_blueprint_agent(project_id: uuid.UUID):
    from database import engine
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project or not project.audit_data:
            print(f"Cannot run blueprint: Missing audit data for {project_id}")
            return

        project.status = ProjectStatus.DESIGNING
        await session.commit()
        
        # Invoke Blueprint Agent
        initial_state = {"genesis_report": project.audit_data}
        result = await blueprint_app.ainvoke(initial_state)
        
        funnel_map = result.get("funnel_blueprint", {})
        
        # Update Project
        project.funnel_structure = funnel_map
        project.status = ProjectStatus.COMPLETED
        session.add(project)
        await session.commit()
        print(f"--- BLUEPRINT COMPLETE FOR PROJECT {project_id} ---")

# --- Routes ---

@app.post("/api/projects/", response_model=ProjectRead)
async def create_project(project_in: ProjectCreate, session: AsyncSession = Depends(get_session)):
    project = Project(
        name=project_in.name,
        niche=project_in.niche,
        user_id=uuid.uuid4() # Mock ID for bypass
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project

@app.get("/api/projects/{project_id}", response_model=ProjectRead)
async def get_project(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.post("/api/run/genesis/{project_id}")
async def trigger_genesis(
    project_id: uuid.UUID, 
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Add background task
    background_tasks.add_task(run_genesis_agent, project_id, None)
    
    return {"message": "Genesis Agent started (Planner -> Research -> Audit)", "project_id": project_id, "status": "processing"}

# ... (Blueprint remains similar but uses new import) ...

# Updated Background Task Logic
async def run_genesis_agent(project_id: uuid.UUID, session_factory):
    from database import engine
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project: return

        project.status = ProjectStatus.ANALYZING
        await session.commit()
        
        # Invoke Genesis Agent (Loop)
        initial_state = {"niche": project.niche, "url": None, "loop_count": 0}
        result = await genesis_app.ainvoke(initial_state)
        
        final_report = result.get("audit_report", {})
        search_results = result.get("search_results", [])
        
        # Update Project
        project.audit_data = final_report
        project.search_results = search_results # New Field
        project.status = ProjectStatus.AUDITED
        session.add(project)
        await session.commit()
        print(f"--- GENESIS COMPLETE FOR PROJECT {project_id} ---")