import logging
import re
import os
import keyring

import google.generativeai as genai
import local_yt_summary as yts
import custom_exceptions as e
import constants


def configure_genai():
    """
    Fetches the API key depending on the runtime environment.
    - Uses keyring if running locally.
    - Reads from Docker secrets if running in Docker.
    """
    try:
        # Check if running inside a Podman container by looking for Podman secrets
        if os.path.exists('/run/secrets/'):
            # Read API key from Podman secrets
            with open("/run/secrets/GOOGLE_AI_API_KEY", "r") as secret_file:
                GOOGLE_AI_API_KEY = secret_file.read().strip()
            logging.info("GOOGLE_AI_API_KEY fetched from Podman secrets.")
        else:
            # Use keyring to fetch the API key locally
            GOOGLE_AI_API_KEY = keyring.get_password("GOOGLE_AI_API_KEY", "GOOGLE_AI_API_KEY")
            if not GOOGLE_AI_API_KEY:
                raise ValueError("GOOGLE_AI_API_KEY not found in keyring.")
            logging.info("GOOGLE_AI_API_KEY fetched from keyring.")
        
        genai.configure(api_key=GOOGLE_AI_API_KEY)

    except Exception as e:
        logging.error("Error fetching GOOGLE_AI_API_KEY: %s", e)
        return None


def create_youtube_summary(message_with_yt_link):
    """Creates a summary of YT video from a message with link.

    Args:
        message_with_yt_link (str): Message with YT link.

    Raises:
        e.GeminiNotWorkingError: When Gemini API doesn't work.

    Returns:
        str: Summary of the video.
    """
    transcript, language = yts.create_transcript(message_with_yt_link)
    if language.startswith("Polish"):
        system_instruction = constants.GEMINI_SYS_INSTRUCTION_YT_PL
    else:
        system_instruction = constants.GEMINI_SYS_INSTRUCTION_YT_EN
    model = genai.GenerativeModel(
        constants.MODEL_GOOGLE_GEMINI["flash_lite"],
        generation_config=constants.GEMINI_LLM_CONFIG,
        system_instruction=system_instruction,
    )
    try:
        response = model.generate_content([transcript[:20000]])
        logging.info(response.text)
        return response.text
    except Exception as exc:
        logging.info("Gemini is not working")
        raise e.GeminiNotWorkingError("Gemini is not working")


def create_discussion_summary(content):
    """Generates the discussion summary. Currently supporting only Polish language.

    Args:
        content (str): Cleaned Discord discussion.

    Returns:
        str: Summary of the discussion.
    """
    model = genai.GenerativeModel(
        constants.MODEL_GOOGLE_GEMINI["flash_lite"],
        generation_config=constants.GEMINI_LLM_CONFIG,
        system_instruction=constants.GEMINI_SYS_INSTRUCTION_DISCUSSION_SUMMARY,
    )
    try:
        response = model.generate_content([f"Rozmowa: {content[:10000]}"])
        logging.debug(response)
        logging.info(response.text)
        return response.text
    except Exception as exc:
        logging.info("Gemini is not working")
        raise e.GeminiNotWorkingError("Gemini is not working")


def describe_thing_pl(thing, channel_for_context, max_words=3, max_word_length=23):
    """Describes the thing passed to the function.
       Uses the channel name as a context.

    Args:
        thing (str): Anything you want to have it described.
        channel_for_context (str): Discord channel name.
        max_words (int): maximum number of words to describe.
        max_word_length (int): maximum word length as users try to bypass max_words.

    Raises:
        e.TooManyWordsError: Too many words passed to the function
        e.TryinToOmitWordsLimitError: Somneone tries to bypass max words limit.
        e.GeminiNotWorkingError: Gemini API is not working.

    Returns:
        str: Description.
    """
    word_count = re.findall(r"\w+", thing)
    if len(word_count) > max_words:
        raise e.TooManyWordsError("Too many words")
    for word in word_count:
        if len(word) > max_word_length:
            raise e.TryinToOmitWordsLimitError("Word too long")
    model = genai.GenerativeModel(
        constants.MODEL_GOOGLE_GEMINI["flash_lite"],
        generation_config=constants.GEMINI_LLM_CONFIG,
        system_instruction=constants.GEMINI_SYS_INSTRUCTION_DESCRIPTION_PL,
    )
    prompt = f"Pojęcie do stworzenia definicji: {thing}\n Nazwa kanału: {channel_for_context}"
    logging.info("Prompt: %s", prompt)
    try:
        response = model.generate_content([prompt])
        logging.debug(response)
        logging.info(response.text)
        return response.text
    except Exception as exc:
        logging.info("Gemini is not working")
        raise e.GeminiNotWorkingError("Gemini is not working")
