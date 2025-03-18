import re
import logging

import constants

from ollama import chat, ChatResponse


def generate_summary(model, content):
    """Generates the summary using Bielik model. Currently supporting only Polish language.

    Args:
        model (str): Bielik LLM.
        content (str): Cleaned Discord discussion.

    Returns:
        str: Summary of the discussion.
    """
    system_instruction = constants.BIELIK_SYS_INSTRUCTION_DISCUSSION_SUMMARY
    messages = [
        {
            "role": "system",
            "content": system_instruction,
        },
        {
            "role": "user",
            "content": f"Rozmowa:{content}",
        },
    ]
    response: ChatResponse = chat(
        model=model,
        stream=False,
        messages=messages,
        options={"num_ctx": 8192, "top_k": 10, "temperature": 0.2, "num_predict": 500},
    )
    logging.info(response["message"]["content"])
    return response["message"]["content"]


def clean_discussion_string(content):
    """Cleans the discussion string from unnecessary text.

    Args:
        content (str): Discord discussion.

    Returns:
        str: Cleaned Discord discussion.
    """
    links_pattern = r"https?://\S+"
    content = re.sub(
        links_pattern,
        "",
        content,
        flags=re.DOTALL,
    )
    ref_pattern = r"<@\d+>"
    content = re.sub(
        ref_pattern,
        "",
        content,
        flags=re.DOTALL,
    )
    emojis_pattern = r"(:\d+>)"
    cleaned_content = re.sub(
        emojis_pattern,
        ":>",
        content,
        flags=re.DOTALL,
    )
    return cleaned_content
