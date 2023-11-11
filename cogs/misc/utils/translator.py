from __future__ import annotations
from typing import TYPE_CHECKING, NamedTuple, TypedDict

from config import LANGUAGES
if TYPE_CHECKING:
    from aiohttp import ClientSession




class TranslateError(Exception):
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code: int = status_code
        self.text: str = text
        super().__init__(f'Google responded with HTTP Status Code {status_code}')


class TranslatedSentence(TypedDict):
    trans: str
    orig: str


class TranslateResult(NamedTuple):
    original: str
    translated: str
    source_language: str
    target_language: str


async def translate(text: str, *, src: str = 'auto', dest: str = 'en', session: ClientSession) -> TranslateResult:
    # This was discovered by the people here:
    # https://github.com/ssut/py-googletrans/issues/268
    query = {
        'dj': '1',
        'dt': ['sp', 't', 'ld', 'bd'],
        'client': 'dict-chrome-ex',
        # Source Language
        'sl': src,
        # Target Language
        'tl': dest,
        # Query
        'q': text,
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'
    }

    target_language = LANGUAGES.get(dest, 'Unknown')

    async with session.get('https://clients5.google.com/translate_a/single', params=query, headers=headers) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise TranslateError(resp.status, text)

        data = await resp.json()
        src = data.get('src', 'Unknown')
        source_language = LANGUAGES.get(src, src)
        sentences: list[TranslatedSentence] = data.get('sentences', [])
        if len(sentences) == 0:
            raise RuntimeError('Google translate returned no information')

        original = ''.join(sentence.get('orig', '') for sentence in sentences)
        translated = ''.join(sentence.get('trans', '') for sentence in sentences)

        return TranslateResult(
            original=original,
            translated=translated,
            source_language=source_language,
            target_language=target_language,
        )