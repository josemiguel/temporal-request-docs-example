import os
from temporalio import activity
from models import DocumentType, DocumentValidation
from google import genai


def get_validation_prompt(document_type: DocumentType, content: str) -> str:
    """Generate validation prompt based on document type."""
    prompts = {
        DocumentType.FULL_NAME: f"""
Validate if the following text contains a valid full name of a person.
A valid full name should:
- Contain at least first name and last name
- Only contain alphabetic characters, spaces, hyphens, or apostrophes
- Not contain numbers or special characters
- Be a plausible human name

Text to validate: "{content}"

Respond with JSON format ONLY:
{{"is_valid": true/false, "message": "explanation"}}
""",
        DocumentType.PASSPORT: f"""
Validate if the following text contains a valid passport number with nationality.
A valid submission should:
- Include a passport number (alphanumeric, typically 6-9 characters)
- Include a nationality/country

Text to validate: "{content}"

Respond with JSON format ONLY:
{{"is_valid": true/false, "message": "explanation"}}
""",
        DocumentType.ADDRESS: f"""
Validate if the following text contains a valid address.
A valid address should:
- Include street name and number
- Optionally include city, state/province, postal code, country

Text to validate: "{content}"

Respond with JSON format ONLY:
{{"is_valid": true/false, "message": "explanation"}}
""",
    }
    return prompts.get(document_type, "")


@activity.defn
async def validate_document(document_type: str, content: str) -> dict:
    """Validate a document using Gemini AI."""
    activity.logger.info(f"Validating document type: {document_type}")

    doc_type = DocumentType(document_type)

    # Configure Gemini
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "document_type": document_type,
            "is_valid": False,
            "message": "Gemini API key not configured. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.",
        }

    client = genai.Client(api_key=api_key)
    prompt = get_validation_prompt(doc_type, content)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        response_text = response.text.strip()

        # Clean up response - remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        import json

        result = json.loads(response_text)

        return {
            "document_type": document_type,
            "is_valid": result.get("is_valid", False),
            "message": result.get("message", "Validation completed"),
        }

    except Exception as e:
        activity.logger.error(f"Error validating document: {e}")
        return {
            "document_type": document_type,
            "is_valid": False,
            "message": f"Validation error: {str(e)}",
        }
