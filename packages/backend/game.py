"""Kanjium全体からの出題と、広い語彙・推定に対応する正解判定。"""
import math
import hashlib
import random
import sqlite3
from collections import defaultdict
from pathlib import Path

from accents import AccentResolver, normalize, kana
from pitch import matching_pattern
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

Difficulty = Literal['easy', 'normal', 'hard']
RANGES = {'easy': (2, 3), 'normal': (4, 5), 'hard': (6, 8)}
MAX_TARGET_FREQUENCY_RANK = 10000


class Rules(BaseModel):
    difficulty: Difficulty = 'easy'
    homophones: bool = False
    recent: list[str] = Field(default_factory=list, max_length=1000)


class Guess(Rules):
    target_id: int
    text: str = Field(min_length=1, max_length=80)


class Catalog:
    def __init__(self, db_path=None, resolver=None):
        root = Path(__file__).parent
        self.resolver = resolver or AccentResolver()
        self.words = {}
        self.readings = defaultdict(list)
        self.surfaces = defaultdict(list)
        self.groups = defaultdict(list)
        self.target_ids = set()
        # 読みではなく表記に対する、小説コーパス内の出現回数。
        frequencies = {}
        with (root / 'vendor/kanjium/data/source_files/raw/novels_freq.txt').open() as stream:
            for line in stream:
                if line.startswith('#') or not line.strip():
                    continue
                surface, count = line.rstrip().split('\t')
                surface = normalize(surface)
                frequencies[surface] = max(frequencies.get(surface, 0), int(count))
        self.frequency_ranks = {text: rank for rank, (text, count) in enumerate(
            sorted(frequencies.items(), key=lambda item: (-item[1], item[0])), 1)}
        self.frequencies = frequencies
        with sqlite3.connect(f'file:{db_path or root / "data/candidates.db"}?mode=ro', uri=True) as conn:
            rows = conn.execute('SELECT id,text,reading,mora_count FROM candidates').fetchall()
        for ident, text, reading, mora in rows:
            try:
                candidates = self.resolver.resolve(text, predict=False)
            except HTTPException:
                continue
            if not candidates:
                continue
            word = next((w for w in candidates if kana(w['reading']) == kana(reading)), candidates[0])
            word = {**word, 'id': ident, 'text': text}
            self.words[ident] = word
            self.readings[kana(word['reading'])].append(word)
            self.surfaces[normalize(text)].append(word)
            for pattern in word['pitch_patterns']:
                self.groups[(word['mora_count'], tuple(pattern))].append(word)

        # 出題はKanjiumの全エントリ（表記・読み）を対象とする。
        existing = {(normalize(w['text']), kana(w['reading'])): w['id'] for w in self.words.values()}
        for entries in self.resolver.surfaces.values():
            for text, reading, accents in entries:
                ident = existing.get((text, reading))
                if ident is not None:
                    self.target_ids.add(ident)
                    continue
                word = self.resolver.word(text, reading, accents, 'kanjium')
                if not word:
                    continue
                ident = -int.from_bytes(hashlib.sha256((text + ':' + reading).encode()).digest()[:6], 'big')
                if ident in self.words:
                    raise ValueError('出題IDが重複しました。')
                word = {**word, 'id': ident}
                self.words[ident] = word
                existing[(text, reading)] = ident
                self.target_ids.add(ident)
                self.readings[kana(word['reading'])].append(word)
                self.surfaces[normalize(text)].append(word)
                for pattern in word['pitch_patterns']:
                    self.groups[(word['mora_count'], tuple(pattern))].append(word)

        self.common_target_ids = {
            ident for ident in self.target_ids
            if self.frequency_ranks.get(normalize(self.words[ident]['text']), MAX_TARGET_FREQUENCY_RANK + 1)
            <= MAX_TARGET_FREQUENCY_RANK
        }
        self.target_surface_counts = defaultdict(int)
        for ident in self.common_target_ids:
            self.target_surface_counts[normalize(self.words[ident]['text'])] += 1

    def alternatives(self, target, rules):
        return (w for p in target['pitch_patterns'] for w in self.groups[(target['mora_count'], tuple(p))]
                if w['key'] != target['key'] and w['key'] not in rules.recent
                and (rules.homophones or w['reading'] != target['reading']))

    def public(self, word, pattern=None):
        pattern = pattern if pattern is not None else word['pitch_patterns'][0]
        return {**word, 'accent_pattern': pattern,
                'accent_code': '・'.join('高' if level == 2 else '低' for level in pattern)}

    def target(self, rules):
        low, high = RANGES[rules.difficulty]
        eligible = [w for w in self.words.values() if w['id'] in self.common_target_ids and low <= w['mora_count'] <= high
                    and w['key'] not in rules.recent and any(self.alternatives(w, rules))]
        if not eligible:
            raise HTTPException(404, 'この条件のお題がありません。履歴をリセットしてください。')
        # 複数の読みを持つ表記が過剰に出題されないよう重みを分配する。
        weights = [math.sqrt(self.frequencies[normalize(w['text'])])
                   / self.target_surface_counts[normalize(w['text'])] for w in eligible]
        return self.public(random.choices(eligible, weights=weights, k=1)[0])

    def guess(self, request):
        target = self.words.get(request.target_id)
        if not target:
            raise HTTPException(404, 'お題が見つかりません。')
        text = normalize(request.text)
        candidates = self.resolver.resolve(text)
        is_kana = all('ァ' <= c <= 'ヶ' or c == 'ー' for c in kana(text))
        message = 'アクセントを比較できませんでした。'
        answer = None
        for w in candidates:
            if w['key'] == target['key'] or normalize(text) == normalize(target['text']):
                message = 'お題とは別の単語を入力してください。'
                continue
            if w['key'] in request.recent:
                message = '最近使った単語です。別の単語を入力してください。'
                continue
            if w['reading'] == target['reading']:
                if not request.homophones:
                    message = '同じ読みの単語は、この設定では正解になりません。'
                    continue
                if is_kana:
                    message = '同音異義語は漢字などで単語を特定してください。'
                    continue
            answer = w
            pattern = matching_pattern(target, w)
            if w['mora_count'] == target['mora_count'] and pattern is not None:
                return dict(correct=True, message='正解！同じ高低のリズムです。', answer=self.public(w, pattern), target=self.public(target, pattern))
            message = '拍数または音の高低の並びが異なります。'
        return dict(correct=False, message=message, answer=self.public(answer) if answer else None, target=self.public(target))


def create_router(catalog=None):
    catalog = catalog or Catalog()
    router = APIRouter(prefix='/api/game')

    @router.post('/target')
    def target(rules: Rules):
        return catalog.target(rules)

    @router.post('/guess')
    def guess(request: Guess):
        return catalog.guess(request)

    return router
