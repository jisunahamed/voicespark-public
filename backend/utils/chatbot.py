import os
import json
import re
import logging
import concurrent.futures
import time

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_TEXT_MODELS = [
    os.getenv('GEMINI_TEXT_MODEL', '').strip(),
    'gemini-2.5-flash',
]
GEMINI_TEXT_TIMEOUT_SECONDS = max(8, min(int(os.getenv('GEMINI_TEXT_TIMEOUT_SECONDS', '30') or 30), 35))
GEMINI_TEXT_MAX_OUTPUT_TOKENS = int(os.getenv('GEMINI_TEXT_MAX_OUTPUT_TOKENS', '8192') or 8192)


class GeminiError(RuntimeError):
    def __init__(self, error_type, message, *, retryable=True, model=''):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable
        self.model = model

    def as_dict(self):
        return {
            'error_type': self.error_type,
            'message': str(self),
            'retryable': self.retryable,
            'model': self.model,
        }


def classify_gemini_error(exc):
    text = str(exc or '')
    upper = text.upper()
    lower = text.lower()
    if isinstance(exc, TimeoutError) or 'timeout' in lower or 'timed out' in lower:
        return 'timeout', True
    if 'RESOURCE_EXHAUSTED' in upper or 'quota' in lower:
        return 'quota_exhausted', True
    if '429' in text or 'rate limit' in lower or 'rate_limited' in lower:
        return 'rate_limited', True
    if 'not found' in lower and 'model' in lower or 'invalid model' in lower:
        return 'invalid_model', False
    if any(marker in lower for marker in ('network', 'connection', 'ssl', 'dns', 'temporarily unavailable')):
        return 'network_error', True
    return 'unknown_error', True


def public_voice_spark_message(error_type, message):
    raw = str(message or '')
    if error_type in ('quota_exhausted', 'rate_limited'):
        return 'Voice Spark AI is temporarily rate limited. Please retry in a few minutes.'
    if error_type == 'timeout':
        return 'Voice Spark AI took too long to respond. Please retry.'
    if error_type == 'invalid_model':
        return 'Voice Spark AI model configuration needs attention.'
    if 'PERMISSION_DENIED' in raw.upper() or 'denied access' in raw.lower():
        return 'Voice Spark AI project access is denied. Check the API key project permissions or billing, then retry.'
    if error_type in ('parse_error', 'invalid_response'):
        if 'GEMINI_API_KEY' in raw or 'GOOGLE_API_KEY' in raw or 'api key' in raw.lower():
            return 'Voice Spark AI key is not configured.'
        return 'Voice Spark AI returned an invalid response. Please retry.'
    if error_type == 'network_error':
        return 'Voice Spark AI could not connect. Please retry.'
    if 'GEMINI_API_KEY' in raw or 'GOOGLE_API_KEY' in raw or 'Gemini' in raw:
        return raw.replace('GEMINI_API_KEY', 'Voice Spark AI key').replace('GOOGLE_API_KEY', 'Voice Spark AI key').replace('Gemini', 'Voice Spark AI')
    return raw or 'Voice Spark AI generation failed. Please retry later.'


def gemini_error_payload(exc, default_message='Voice Spark AI generation failed. Please retry later.'):
    if isinstance(exc, GeminiError):
        payload = exc.as_dict()
        payload['message'] = public_voice_spark_message(payload['error_type'], payload['message'])
        return payload
    error_type, retryable = classify_gemini_error(exc)
    return {
        'error_type': error_type,
        'message': public_voice_spark_message(error_type, str(exc) or default_message),
        'retryable': retryable,
        'model': '',
    }


def run_with_timeout(fn, timeout_seconds):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise TimeoutError(f'Gemini text generation timed out after {timeout_seconds}s') from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


class _GeminiChoice:
    def __init__(self, content):
        self.message = type('Message', (), {'content': content})()


class _GeminiCompletion:
    def __init__(self, content):
        self.choices = [_GeminiChoice(content)]


class GeminiTextGenerator:
    """Google Gemini text generator used for all AI text tasks."""

    def __init__(self):
        self.client = None
        self.chat_completion = None
        self.chat_history = []
        self.last_error = None

    def create_client(self):
        from google import genai

        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise RuntimeError('GEMINI_API_KEY is not configured.')
        self.client = genai.Client(api_key=api_key)

    def create_system_normal_goal(self, index, objective):
        self.chat_history.append(self.create_content(
            role='system',
            content=(
                'This is an objective prompt. Anything written here if it conflicts with the BASE PROMPT shall be ignored. '
                'The messages that are given to the other person linkedin account should meet the following objective, '
                'but it should NOT disrupt the flow of messages that are being received and sent. '
                f'Gradually fulfill the objectives serially by the index. Objective {index}: {objective}'
            ),
        ))

    def clear_chat_history(self):
        if not self.chat_history:
            return
        system_content = self.chat_history[0]
        self.chat_history = [system_content]

    def create_system_prompt(self, content):
        self.chat_history.append(self.create_content(role='system', content=content))

    def send_users_message(self, message):
        self.chat_history.append(self.create_content(role='user', content=message))

    def send_assistant_message(self, message):
        self.chat_history.append(self.create_content(role='assistant', content=message))

    def create_content(self, role: str, content: str) -> dict:
        return {'role': role, 'content': content}

    def _split_messages(self):
        system_parts = []
        user_parts = []
        for item in self.chat_history:
            role = item.get('role')
            content = str(item.get('content') or '')
            if role == 'system':
                system_parts.append(content)
            elif role == 'assistant':
                user_parts.append(f'Assistant context:\n{content}')
            else:
                user_parts.append(content)
        return '\n\n'.join(system_parts).strip(), '\n\n'.join(user_parts).strip()

    def create_chat_completion(self, google_search=False, response_mime_type=None):
        if self.client is None:
            self.create_client()
        system_instruction, prompt = self._split_messages()
        if not prompt:
            prompt = system_instruction or 'Generate a response.'
            system_instruction = ''

        try:
            from google.genai import types
        except Exception:
            types = None

        if response_mime_type and google_search:
            prompt = (
                f"{prompt}\n\n"
                "Return only valid JSON. Do not include markdown fences, citations, or explanation outside the JSON."
            )

        model_candidates = [model for model in GEMINI_TEXT_MODELS if model]
        started = time.monotonic()
        for model in dict.fromkeys(model_candidates):
            try:
                kwargs = {'model': model, 'contents': prompt}
                if types:
                    config_kwargs = {}
                    if system_instruction:
                        config_kwargs['system_instruction'] = system_instruction
                    if GEMINI_TEXT_MAX_OUTPUT_TOKENS:
                        config_kwargs['max_output_tokens'] = GEMINI_TEXT_MAX_OUTPUT_TOKENS
                    if response_mime_type and not google_search:
                        config_kwargs['response_mime_type'] = response_mime_type
                    if google_search:
                        config_kwargs['tools'] = [types.Tool(google_search=types.GoogleSearch())]
                    if config_kwargs:
                        kwargs['config'] = types.GenerateContentConfig(**config_kwargs)
                response = run_with_timeout(
                    lambda current_kwargs=kwargs: self.client.models.generate_content(**current_kwargs),
                    GEMINI_TEXT_TIMEOUT_SECONDS,
                )
                text = (getattr(response, 'text', None) or '').strip()
                if not text and getattr(response, 'candidates', None):
                    parts = getattr(response.candidates[0].content, 'parts', []) or []
                    text = ''.join(getattr(part, 'text', '') or '' for part in parts).strip()
                if text:
                    self.chat_completion = _GeminiCompletion(text)
                    logger.info(
                        "Gemini text request completed model=%s elapsed_ms=%s json_mode=%s search=%s chars=%s",
                        model,
                        int((time.monotonic() - started) * 1000),
                        bool(response_mime_type),
                        bool(google_search),
                        len(text),
                    )
                    return
            except Exception as exc:
                self.last_error = exc
                error_text = str(exc)
                error_type, retryable = classify_gemini_error(exc)
                logger.warning("Gemini text model %s failed type=%s retryable=%s: %s", model, error_type, retryable, error_text[:400])
                if error_type in ('quota_exhausted', 'rate_limited', 'invalid_model'):
                    break
                continue
        error_type, retryable = classify_gemini_error(self.last_error)
        logger.warning("Gemini text completion failed type=%s retryable=%s: %s", error_type, retryable, self.last_error)
        raise GeminiError(error_type, str(self.last_error) or 'Gemini returned no text.', retryable=retryable)

    def get_generated_message(self) -> str:
        try:
            return self.chat_completion.choices[0].message.content
        except Exception as exc:
            logger.warning("Failed to read generated output: %s", exc)
            return ''

    def create_base_system_prompt(self):
        self.create_system_prompt("Remove any emojis. Answer in markdown by default unless asked not to.")

    def temporary_chat_system(self):
        self.create_base_system_prompt()
        self.send_users_message('Say hello.')
        self.create_chat_completion()
        logger.debug("temporary chat response: %s", self.get_generated_message())


ChatGPT = GeminiTextGenerator


def parse_json_response(text):
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?|```", "", str(text)).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
            return parsed
        except json.JSONDecodeError:
            continue
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def gemini_text(prompt, system_prompt='', google_search=False, json_mode=False):
    cg = GeminiTextGenerator()
    cg.create_client()
    if system_prompt:
        cg.create_system_prompt(system_prompt)
    cg.send_users_message(prompt)
    cg.create_chat_completion(
        google_search=google_search,
        response_mime_type='application/json' if json_mode else None,
    )
    text = cg.get_generated_message()
    if not text:
        raise GeminiError('invalid_response', 'Gemini returned an empty response.', retryable=True)
    return text


def gemini_json(prompt, system_prompt='', google_search=False, fallback=None):
    text = gemini_text(prompt, system_prompt=system_prompt, google_search=google_search, json_mode=True)
    parsed = parse_json_response(text)
    if parsed is None:
        text = gemini_text(prompt, system_prompt=system_prompt, google_search=google_search, json_mode=False)
        parsed = parse_json_response(text)
    if parsed is None:
        logger.warning("Gemini JSON parse failed raw_prefix=%s", text[:500])
        if fallback is not None:
            return fallback
        raise GeminiError('parse_error', 'Gemini returned malformed JSON.', retryable=True)
    return parsed


if __name__ == "__main__":
    cg = GeminiTextGenerator()
    cg.create_client()
    cg.temporary_chat_system()
