from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    MENTOR = "MENTOR"
    EMPLOYEE = "EMPLOYEE"
    TEAM_LEAD = "TEAM_LEAD"
    LD_MANAGER = "LD_MANAGER"


class EnrollmentStatus(StrEnum):
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ReportStatus(StrEnum):
    PENDING = "PENDING"       # На проверке
    ACCEPTED = "ACCEPTED"     # Принято
    REVISION = "REVISION"     # На доработку
