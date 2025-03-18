import re

import custom_exceptions as e
import constants

from youtube_transcript_api import YouTubeTranscriptApi
from ollama import chat, ChatResponse


def generate_pl_summary(model, transcript):
    """Creates the LLM Polish response which summarizes the given transcript.

    Args:
        model (str): Model goot at Polish.
        transcript (str): Transcript pulled from YouTubeTranscriptAPI.

    Returns:
        str: Summary of the transcript created by the model.
    """
    system_instruction = constants.BIELIK_SYS_INSTRUCTION_YT
    messages = [
        {
            "role": "system",
            "content": system_instruction,
        },
        {
            "role": "user",
            "content": f"Transcript to summarize:{transcript}",
        },
    ]

    response: ChatResponse = chat(
        model=model,
        stream=False,
        messages=messages,
        options=constants.SETTINGS_YT_SUMMARY,
    )
    pattern = "<think>.*?</think>"
    valid_response = re.sub(
        pattern, "", response["message"]["content"], flags=re.DOTALL
    )
    print(valid_response[:2000])
    return valid_response[:2000]


def generate_en_summary(model, transcript):
    """Creates the LLM response which summarizes the given transcript

    Args:
        model (str): Used model.
        transcript (str): Transcript pulled from YouTubeTranscriptAPI.

    Returns:
        str: Summary of the transcript created by the model.
    """
    system_instruction = constants.DEEPSEEK_SYS_INSTRUCTION_YT
    messages = [
        {
            "role": "system",
            "content": system_instruction,
        },
        {
            "role": "user",
            "content": f"Text to summarize:{transcript}",
        },
    ]

    response: ChatResponse = chat(
        model=model, messages=messages, options=constants.SETTINGS_YT_SUMMARY
    )
    pattern = "<think>.*?</think>"
    valid_response = re.sub(
        pattern, "", response["message"]["content"], flags=re.DOTALL
    )
    print(valid_response[:2000])
    return valid_response


def extract_youtube_id(text_with_yt_link):
    """Extracts the YouTube video ID from the link (can be included in the text)

    Args:
        link (str): YouTube video link or text containing it.

    Raises:
        ValueError: YouTube video link not present.

    Returns:
        str: YouTube video ID
    """
    match_youtube = re.search(r"v=([a-zA-Z0-9_-]{11})", text_with_yt_link)
    match_youtu_be = re.search(r"youtu\.be\/([^\?\/]+)", text_with_yt_link)
    if match_youtube:
        return match_youtube.group(1)
    if match_youtu_be:
        return match_youtu_be.group(1)
    raise ValueError("Invalid YouTube link")


def create_transcript(text_with_yt_link):
    """Creates the transcript of the YouTube video. Doesn't work with shorts.
    For now only Polish and English languages are supported.

    Args:
        text_with_yt_link (str): Text containing

    Raises:
        e.MissingTranscriptError: Missing transcript or transcript language not supported

    Returns:
        final_transcript (str): Transcript of the video.
        transcript_language (str): Language of the transcript.
    """
    yt_id = extract_youtube_id(text_with_yt_link)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(yt_id, languages=["pl", "en"])
    except:
        raise e.MissingTranscriptError(
            "Missing transcript or transcript language not supported"
        )
    transcript_list = YouTubeTranscriptApi.list_transcripts(yt_id)
    transcript_lang = transcript_list.find_transcript(["pl", "en"])
    transcript_language = transcript_lang.language
    final_transcript = " ".join([item["text"] for item in transcript])
    return final_transcript, transcript_language


def generate_summary(message_with_yt_link, ez_mode):
    """Summarizes the YouTube video linked in the message.

    Args:
        message (str): Message with YouTube video link.
        args: Uses the smaller model when ez_mode flag is on.

    Returns:
        str: Video summary.
    """
    transcript, language = create_transcript(message_with_yt_link)
    if ez_mode:
        model_size = "ez"
    else:
        model_size = "normal"
    if language.startswith("Polish"):
        summary = generate_pl_summary(
            constants.MODEL_YT_SUMMARY_PL_LOCAL[model_size], transcript
        )
        return summary
    if language.startswith("English"):
        summary = generate_en_summary(
            constants.MODEL_YT_SUMMARY_PL_LOCAL[model_size], transcript
        )
        return summary
