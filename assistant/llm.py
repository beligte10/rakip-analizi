"""
assistant.llm
==============
OpenAI uyumlu /chat/completions ucuna akışlı istemci — Qwen'e ya Alibaba
Model Studio "compatible-mode" ya da OpenRouter üzerinden erişilir
(anahtar "sk-or-" ile başlıyorsa varsayılan OpenRouter). Yeni bağımlılık eklememek için yalnız
standart kütüphane (urllib) kullanır.

stream_chat() şu olayları üretir:
    ('content', metin)            yanıt parçası
    ('tool_calls', [..])          tur sonunda birikmiş araç çağrıları
    ('finish', finish_reason)
Hata durumunda LLMError fırlatır (mesajı kullanıcıya gösterilebilir).
"""
from __future__ import annotations

import json
import re
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

DEFAULT_BASE = 'https://maas.qwencloudapi.com/compatible-mode/v1'
DEFAULT_MODEL = 'qwen3.5-plus'
OPENROUTER_BASE = 'https://openrouter.ai/api/v1'
OPENROUTER_MODEL = 'qwen/qwen3.5-plus-20260420'


# Qwen yanıtlarında ara sıra Çince/Japonca/Korece kelime sızıyor (ör. "stratejik对标"). Türkçe/İngilizce
# arayüzde bu karakterlerin yeri yok; metin kullanıcıya gitmeden temizlenir (2026-10-03).
_CJK = re.compile(r'[\u2E80-\u2FFF\u3000-\u303F\u3040-\u30FF\u3100-\u31FF\u3400-\u4DBF\u4E00-\u9FFF'
                  r'\uAC00-\uD7AF\uF900-\uFAFF\uFF00-\uFF60]+')


def cjk_temizle(metin: str) -> str:
    return _CJK.sub('', metin) if metin else metin


class LLMError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    api_key: str
    base_url: str = DEFAULT_BASE
    model: str = DEFAULT_MODEL
    enable_thinking: bool = False
    timeout: float = 90.0

    @property
    def is_openrouter(self) -> bool:
        return 'openrouter.ai' in self.base_url

    @classmethod
    def from_env(cls) -> Optional['LLMConfig']:
        """QWEN_API_KEY / OPENROUTER_API_KEY / DASHSCOPE_API_KEY yoksa None — asistan kapalı."""
        key = (os.environ.get('QWEN_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
               or os.environ.get('DASHSCOPE_API_KEY'))
        if not key:
            return None
        openrouter = key.startswith('sk-or-')
        return cls(
            api_key=key,
            base_url=(os.environ.get('QWEN_API_BASE')
                      or (OPENROUTER_BASE if openrouter else DEFAULT_BASE)).rstrip('/'),
            model=os.environ.get('QWEN_MODEL') or (OPENROUTER_MODEL if openrouter else DEFAULT_MODEL),
            enable_thinking=os.environ.get('QWEN_ENABLE_THINKING', '0').lower() in ('1', 'true', 'yes'),
            timeout=float(os.environ.get('QWEN_TIMEOUT', '90')),
        )


def _http_error_message(code: int) -> str:
    if code in (401, 403):
        return 'Yapay zeka servisi anahtarı reddetti (API anahtarını kontrol edin).'
    if code == 402:
        return 'Yapay zeka servisinde bakiye/kredi yetersiz.'
    if code == 404:
        return 'Yapay zeka servisi adresi ya da model adı bulunamadı (QWEN_API_BASE / QWEN_MODEL).'
    if code == 429:
        return 'Yapay zeka servisi şu an yoğun ya da kota doldu; biraz sonra tekrar deneyin.'
    if code >= 500:
        return 'Yapay zeka servisinde geçici bir hata oluştu; tekrar deneyin.'
    return f'Yapay zeka servisi isteği reddetti (HTTP {code}).'


def stream_chat(cfg: LLMConfig, messages: List[dict], tools: Optional[List[dict]] = None,
                temperature: float = 0.2) -> Iterator[Tuple[str, object]]:
    body = {
        'model': cfg.model,
        'messages': messages,
        'stream': True,
        'temperature': temperature,
    }
    # Düşünme modu: OpenRouter'da birleşik "reasoning" parametresi, Model
    # Studio'da Qwen'e özel "enable_thinking".
    if cfg.is_openrouter:
        body['reasoning'] = {'enabled': cfg.enable_thinking}
    else:
        body['enable_thinking'] = cfg.enable_thinking
    if tools:
        body['tools'] = tools
    req = urllib.request.Request(
        cfg.base_url + '/chat/completions',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Accept': 'text/event-stream',
                 'Authorization': f'Bearer {cfg.api_key}',
                 'X-Title': 'KT Rakip Analizi'},
        method='POST',
    )
    try:
        resp = urllib.request.urlopen(req, timeout=cfg.timeout)
    except urllib.error.HTTPError as e:
        raise LLMError(_http_error_message(e.code)) from None
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError):
        raise LLMError('Yapay zeka servisine ulaşılamadı (ağ bağlantısı ya da QWEN_API_BASE).') from None

    calls: dict = {}          # index → {id, name, arguments}
    finish = None
    try:
        with resp:
            for raw in resp:
                line = raw.decode('utf-8', 'replace').strip()
                if not line.startswith('data:'):
                    continue
                data = line[5:].strip()
                if data == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                if chunk.get('error'):
                    raise LLMError('Yapay zeka servisi hata döndürdü: '
                                   + str((chunk['error'] or {}).get('message', ''))[:200])
                for ch in chunk.get('choices') or []:
                    delta = ch.get('delta') or {}
                    if delta.get('content'):
                        yield ('content', delta['content'])
                    for tc in delta.get('tool_calls') or []:
                        slot = calls.setdefault(tc.get('index', 0), {'id': None, 'name': '', 'arguments': ''})
                        if tc.get('id'):
                            slot['id'] = tc['id']
                        fn = tc.get('function') or {}
                        if fn.get('name'):
                            slot['name'] += fn['name']
                        if fn.get('arguments'):
                            slot['arguments'] += fn['arguments']
                    if ch.get('finish_reason'):
                        finish = ch['finish_reason']
    except (socket.timeout, TimeoutError):
        raise LLMError('Yapay zeka servisi zamanında yanıt vermedi.') from None
    except OSError:
        raise LLMError('Yapay zeka servisiyle bağlantı koptu.') from None

    if calls:
        out = []
        for i in sorted(calls):
            c = calls[i]
            out.append({'id': c['id'] or f'call_{i}', 'type': 'function',
                        'function': {'name': c['name'], 'arguments': c['arguments'] or '{}'}})
        yield ('tool_calls', out)
    yield ('finish', finish or ('tool_calls' if calls else 'stop'))
