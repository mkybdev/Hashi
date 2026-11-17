"""Kanjium、UniDic、推定の順で回答を解析する。"""
import logging
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from threading import RLock

from pitch import from_kernel

import MeCab
import unidic
from fastapi import HTTPException
from sudachipy import dictionary
from tdmelodic.nn.lang.japanese.kana.mora_sep import sep_katakana2mora


def normalize(text):
    return unicodedata.normalize('NFKC', text).strip()


def kana(text):
    return ''.join(chr(ord(c) + 96) if 'ぁ' <= c <= 'ゖ' else c for c in normalize(text))


class AccentResolver:
    def __init__(self, predictor=None):
        self.predictor = predictor
        self.lock = RLock()
        root = Path(__file__).parent
        self.tagger = MeCab.Tagger(f'-d "{unidic.DICDIR}" -r "{root / "mecabrc"}" -Oacc')
        self.tokenizer = dictionary.Dictionary(dict='small').create()
        self.surfaces = defaultdict(list)
        self.readings = defaultdict(list)
        with (root / 'vendor/kanjium/data/source_files/raw/accents.txt').open() as stream:
            for row in csv.reader(stream, delimiter='\t'):
                if len(row) != 3:
                    raise ValueError('Kanjiumのデータ形式が不正です。')
                surface, reading, raw = row
                accents = [int(a) for a in raw.split(',') if a.isdigit()]
                if accents:
                    # 上流ではかな表記と同じ読みを空欄で省略する。
                    if not reading:
                        surface_reading = kana(surface)
                        if not surface_reading or not all('ァ' <= c <= 'ヶ' or c == 'ー' for c in surface_reading):
                            continue
                        reading = surface_reading
                    entry = (normalize(surface), kana(reading), accents)
                    self.surfaces[entry[0]].append(entry)
                    self.readings[entry[1]].append(entry)

    def word(self, text, reading, accents, source, patterns=None):
        reading = kana(reading)
        mora = len(sep_katakana2mora(reading))
        accents = sorted(set(a for a in accents if 0 <= a <= mora))
        if patterns is None:
            patterns = [from_kernel(mora, accent) for accent in accents]
        patterns = [list(p) for p in dict.fromkeys(tuple(p) for p in patterns)
                    if len(p) == mora and all(level in (1, 2) for level in p)]
        if not patterns or not mora:
            return None
        tokens = self.tokenizer.tokenize(text)
        lemma = ''.join(t.normalized_form() for t in tokens)
        return dict(id=0, text=text, reading=reading, mora_count=mora, accents=accents,
                    key=lemma + ':' + reading, source=source, estimated=source == 'tdmelodic', pitch_patterns=patterns)

    def resolve(self, text, predict=True):
        text = normalize(text)
        if not text or len(text) > 80 or not re.fullmatch(r'[\w々〆ヶー・]+', text) or not re.search(r'[ぁ-ゖァ-ヶ一-龥]', text):
            raise HTTPException(400, '日本語の単語を1語入力してください。')
        with self.lock:
            entries = self.surfaces.get(text)
            is_kana = all('ァ' <= c <= 'ヶ' or c == 'ー' for c in kana(text))
            if not entries and is_kana:
                entries = self.readings.get(kana(text))
            if entries:
                # 漢字の多読語は通常の読みで照合し、別の読みへの偶然の一致を防ぐ。
                if not is_kana:
                    preferred = kana(''.join(t.reading_form() for t in self.tokenizer.tokenize(text)))
                    matching = [entry for entry in entries if entry[1] == preferred]
                    if matching:
                        entries = matching
                words = [w for surface, reading, accents in entries
                         if (w := self.word(surface, reading, accents, 'kanjium'))]
                if words:
                    return words
            parsed = [line.split('\t') for line in self.tagger.parse(text).splitlines() if line != 'EOS']
            if len(parsed) == 1 and len(parsed[0]) >= 6:
                fields = parsed[0]
                accents = [int(a) for a in fields[5].split(',') if a.isdigit()]
                if accents:
                    word = self.word(text, fields[1], accents, 'unidic')
                    if word:
                        return [word]
            if not predict:
                return []
            tokens = self.tokenizer.tokenize(text)
            if len(tokens) > 1 and any(t.part_of_speech()[0] in ('助詞', '助動詞') for t in tokens):
                raise HTTPException(400, '文章ではなく単語を入力してください。')
            reading = ''.join(t.reading_form() for t in tokens)
            if not all('ァ' <= c <= 'ヶ' or c == 'ー' for c in kana(reading)):
                raise HTTPException(400, '読みを取得できませんでした。かなで入力してください。')
            if self.predictor is None:
                from main import converter
                self.predictor = converter.predict_pitch
            try:
                pattern = self.predictor(text, reading)
            except (ValueError, KeyError, IndexError, TypeError, RuntimeError) as error:
                logging.getLogger(__name__).exception('tdmelodicでアクセント推定に失敗: %s', text)
                raise HTTPException(422, 'アクセントを推定できませんでした。別の表記やかな入力をお試しください。') from error
            word = self.word(text, reading, [], 'tdmelodic', patterns=[pattern])
            if not word:
                raise HTTPException(400, 'アクセントを推定できませんでした。')
            return [word]
