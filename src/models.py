from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

# Association table for many-to-many relationship between activities and participants
activity_participants = Table(
    'activity_participants',
    Base.metadata,
    Column('activity_id', Integer, ForeignKey('activities.id'), primary_key=True),
    Column('participant_email', String, ForeignKey('participants.email'), primary_key=True)
)

class Activity(Base):
    __tablename__ = 'activities'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[str] = mapped_column(String)
    schedule: Mapped[str] = mapped_column(String)
    max_participants: Mapped[int] = mapped_column(Integer)

    # Many-to-many relationship with participants
    participants: Mapped[list["Participant"]] = relationship(
        "Participant", secondary=activity_participants, back_populates="activities"
    )

class Participant(Base):
    __tablename__ = 'participants'

    email: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Many-to-many relationship with activities
    activities: Mapped[list[Activity]] = relationship(
        "Activity", secondary=activity_participants, back_populates="participants"
    )