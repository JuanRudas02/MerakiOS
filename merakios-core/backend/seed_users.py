import asyncio
from sqlmodel import select
from database import init_db, get_session, engine
from models import User
from auth import get_password_hash
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

async def seed_users():
    print("--- SEEDING USERS ---")
    await init_db() # Ensure tables exist
    
    users_to_create = [
        {"email": "juan1007120484@gmail.com", "password": "2527Juan@"},
        {"email": "admin@merakios.com", "password": "adminpassword"},
        {"email": "demo@merakios.com", "password": "demopassword"}
    ]
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for u in users_to_create:
            # Check if exists
            statement = select(User).where(User.email == u["email"])
            result = await session.execute(statement)
            existing_user = result.scalars().first()
            
            pwd_hash = get_password_hash(u["password"])
            
            if not existing_user:
                new_user = User(
                    email=u["email"],
                    password_hash=pwd_hash
                )
                session.add(new_user)
                print(f"Created user: {u['email']}")
            else:
                existing_user.password_hash = pwd_hash
                session.add(existing_user)
                print(f"Updated password for: {u['email']}")
        
        await session.commit()
    print("--- SEEDING COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(seed_users())
