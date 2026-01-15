from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DocumentType(str, Enum):
    FULL_NAME = "full_name"
    PASSPORT = "passport"
    ADDRESS = "address"


@dataclass
class DocumentSubmission:
    document_type: DocumentType
    content: str


@dataclass
class DocumentValidation:
    document_type: DocumentType
    is_valid: bool
    message: str


@dataclass
class DocumentStatus:
    full_name: Optional[DocumentValidation] = None
    passport: Optional[DocumentValidation] = None
    address: Optional[DocumentValidation] = None

    def all_valid(self) -> bool:
        return (
            self.full_name is not None
            and self.full_name.is_valid
            and self.passport is not None
            and self.passport.is_valid
            and self.address is not None
            and self.address.is_valid
        )

    def to_dict(self) -> dict:
        return {
            "full_name": {
                "is_valid": self.full_name.is_valid if self.full_name else None,
                "message": self.full_name.message if self.full_name else "Not submitted",
            },
            "passport": {
                "is_valid": self.passport.is_valid if self.passport else None,
                "message": self.passport.message if self.passport else "Not submitted",
            },
            "address": {
                "is_valid": self.address.is_valid if self.address else None,
                "message": self.address.message if self.address else "Not submitted",
            },
        }


@dataclass
class WorkflowState:
    status: str
    documents: dict
    all_valid: bool
    completed: bool
