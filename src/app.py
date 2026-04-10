"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import os
from pathlib import Path
from .database import get_db, create_tables
from .models import Activity, Participant

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Initial activities data
initial_activities = [
    {
        "name": "Chess Club",
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    {
        "name": "Programming Class",
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    {
        "name": "Gym Class",
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    {
        "name": "Basketball",
        "description": "Team basketball practices and intramural games",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 15,
        "participants": ["james@mergington.edu"]
    },
    {
        "name": "Track and Field",
        "description": "Running, jumping, and athletic competition events",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 25,
        "participants": ["alex@mergington.edu", "sarah@mergington.edu"]
    },
    {
        "name": "Debate Club",
        "description": "Develop critical thinking and public speaking through debate competitions",
        "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 16,
        "participants": ["benjamin@mergington.edu", "isabella@mergington.edu"]
    },
    {
        "name": "Robotics Club",
        "description": "Build and program robots for competitions and projects",
        "schedule": "Mondays and Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 18,
        "participants": ["lucas@mergington.edu"]
    },
    {
        "name": "Art Studio",
        "description": "Painting, drawing, and sculpture techniques",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 20,
        "participants": ["grace@mergington.edu", "maya@mergington.edu"]
    },
    {
        "name": "Music Band",
        "description": "Learn and perform instrumental music in an ensemble",
        "schedule": "Mondays, Wednesdays, Fridays, 3:30 PM - 4:30 PM",
        "max_participants": 25,
        "participants": ["harper@mergington.edu"]
    }
]

@app.on_event("startup")
async def startup_event():
    await create_tables()
    # Populate initial data only if not in test mode
    if os.getenv("TESTING") != "1":
        # Populate initial data
        async for db in get_db():
            for activity_data in initial_activities:
                # Check if activity already exists
                result = await db.execute(select(Activity).where(Activity.name == activity_data["name"]))
                existing = result.scalars().first()
                if not existing:
                    activity = Activity(
                        name=activity_data["name"],
                        description=activity_data["description"],
                        schedule=activity_data["schedule"],
                        max_participants=activity_data["max_participants"]
                    )
                    db.add(activity)
                    await db.commit()
                    await db.refresh(activity)
                    # Add participants
                    for email in activity_data["participants"]:
                        participant = Participant(email=email)
                        db.add(participant)
                        activity.participants.append(participant)
                    await db.commit()
            break  # Only do this once


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
async def get_activities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Activity).options(selectinload(Activity.participants)))
    activities = result.scalars().all()
    # Convert to dict format for compatibility
    activities_dict = {}
    for activity in activities:
        activities_dict[activity.name] = {
            "description": activity.description,
            "schedule": activity.schedule,
            "max_participants": activity.max_participants,
            "participants": [p.email for p in activity.participants]
        }
    return activities_dict


@app.post("/activities/{activity_name}/signup")
async def signup_for_activity(activity_name: str, email: str, db: AsyncSession = Depends(get_db)):
    """Sign up a student for an activity"""
    # Validate activity exists
    result = await db.execute(select(Activity).where(Activity.name == activity_name))
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check if student is already signed up
    result = await db.execute(select(Participant).where(Participant.email == email))
    participant = result.scalars().first()
    if participant and activity in participant.activities:
        raise HTTPException(status_code=400, detail="Student already signed up for this activity")

    # Create participant if not exists
    if not participant:
        participant = Participant(email=email)
        db.add(participant)
        await db.commit()
        await db.refresh(participant)

    # Add to activity
    activity.participants.append(participant)
    await db.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/signup")
async def unregister_from_activity(activity_name: str, email: str, db: AsyncSession = Depends(get_db)):
    """Unregister a student from an activity"""
    # Validate activity exists
    result = await db.execute(select(Activity).where(Activity.name == activity_name))
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Find participant
    result = await db.execute(select(Participant).where(Participant.email == email))
    participant = result.scalars().first()
    if not participant or activity not in participant.activities:
        raise HTTPException(status_code=400, detail="Student not signed up for this activity")

    # Remove from activity
    activity.participants.remove(participant)
    await db.commit()

