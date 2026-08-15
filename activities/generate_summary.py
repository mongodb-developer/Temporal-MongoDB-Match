from temporalio import activity
import config

def fallback_summary(payload: dict) -> str:
    trials = payload["trials"]
    if not trials:
        return "No eligible synthetic trials were found for the selected constraints."

    lines = ["Top synthetic trial matches:"]
    for trial in trials[:3]:
        lines.append(
            f"- {trial['trialId']} — {trial['title']} "
            f"(vector score {trial['score']:.3f}, "
            f"{trial['distanceMiles']:.1f} miles away)"
        )
    return "\n".join(lines)

@activity.defn(name="generate_summary")
def generate_summary(payload: dict) -> str:
    fallback = fallback_summary(payload)

    if not config.OPENAI_API_KEY:
        return fallback

    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.responses.create(
        model=config.OPENAI_MODEL,
        input=(
            "Summarize these SYNTHETIC clinical-trial matches for a technical demo. "
            "Do not provide medical advice. Preserve trial IDs and distances.\n\n"
            + fallback
        ),
    )
    return response.output_text.strip()
