from temporalio import activity
from config import settings
from database import get_db

@activity.defn(name="extract_ehr")
def extract_ehr(patient_id: str) -> dict:
    patient = get_db().patients.find_one({"_id": patient_id})
    if not patient:
        raise ValueError(f"Patient not found: {patient_id}")

    fallback = (
        f"Patient age {patient['age']} with {patient['diagnosis']}, "
        f"stage {patient['stage']}. Symptoms: {', '.join(patient['symptoms'])}. "
        f"Current medications: {', '.join(patient['medications'])}."
    )

    search_text = fallback

    if settings.openai_api_key:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_model,
            input=(
                "Normalize this SYNTHETIC EHR profile into one concise clinical-trial "
                "search query. Do not invent facts.\n\n" + fallback
            ),
        )
        search_text = response.output_text.strip()

    return {
        "patientId": patient["_id"],
        "age": patient["age"],
        "stage": patient["stage"],
        "diagnosis": patient["diagnosis"],
        "symptoms": patient["symptoms"],
        "medications": patient["medications"],
        "location": patient["location"],
        "searchText": search_text,
    }
