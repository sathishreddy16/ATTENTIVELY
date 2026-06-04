from enum import Enum


class SessionStatus(str, Enum):
    created = "created"
    upload_initialized = "upload_initialized"
    uploading = "uploading"
    analysis_pending = "analysis_pending"
    completed = "completed"
    failed = "failed"


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    enqueue_failed = "enqueue_failed"


class FlagColor(str, Enum):
    yellow = "yellow"
    red = "red"
    gray = "gray"


class IssueType(str, Enum):
    pronunciation = "pronunciation"
    missing_word = "missing_word"
    interruption = "interruption"
    ambiguous = "ambiguous"


class RetentionChoice(str, Enum):
    keep = "keep"
    delete = "delete"
