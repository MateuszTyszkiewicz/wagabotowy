class MissingTranscriptError(Exception):
    "Raised when YT video trascript in unavilable or in unsupported language."


class GeminiNotWorkingError(Exception):
    "Raised when Gemini API is not working for some reason."


class TooManyWordsError(Exception):
    "Raised when someone wants to pass too many words to coto function."


class TryinToOmitWordsLimitError(Exception):
    "Raised when someone wants to bypass word limiter in coto function."
