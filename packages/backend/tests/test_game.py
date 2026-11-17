"""実辞書で正解条件と出題可能性を検証する。"""
import unittest
from game import Catalog, Guess, Rules, MAX_TARGET_FREQUENCY_RANK
from accents import AccentResolver, normalize
from fastapi import HTTPException


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog()

    def word(self, text):
        return next(w for w in self.catalog.words.values() if w['text'] == text)

    def test_kana_and_same_word(self):
        target = self.word('優位')
        for text in ['周囲', 'しゅうい', 'シュウイ']:
            self.assertTrue(self.catalog.guess(Guess(target_id=target['id'], text=text))['correct'])
        for text in ['優位', 'ゆうい']:
            self.assertFalse(self.catalog.guess(Guess(target_id=target['id'], text=text))['correct'])

    def test_full_prediction_pattern_is_compared(self):
        import copy
        catalog = copy.copy(self.catalog)
        catalog.words = dict(catalog.words)
        catalog.words[-1] = dict(id=-1, text='テスト対象', reading='ターゲット', key='target',
                                mora_count=5, accents=[], source='tdmelodic', estimated=True,
                                pitch_patterns=[[1, 2, 1, 2, 1]])
        catalog.resolver = AccentResolver(predictor=lambda text, reading: [1, 2, 1, 1, 1])
        result = catalog.guess(Guess(target_id=-1, text='ハシゲーム'))
        self.assertFalse(result['correct'])  # 最初の下降が同じでも、後半が異なる。
        catalog.words[-1]['pitch_patterns'].append([1, 2, 1, 1, 1])
        result = catalog.guess(Guess(target_id=-1, text='ハシゲーム'))
        self.assertTrue(result['correct'])
        self.assertEqual(result['target']['accent_pattern'], [1, 2, 1, 1, 1])

    def test_sentence_rejected(self):
        with self.assertRaises(HTTPException):
            self.catalog.resolver.resolve('これは文章です')

    def test_priority_and_unknown_words(self):
        calls = []
        resolver = AccentResolver(predictor=lambda text, reading: calls.append(text) or [1, 2, 1, 1, 1])
        self.assertEqual(resolver.resolve('優位')[0]['source'], 'kanjium')
        unidic_word = next(w for w in self.catalog.words.values() if w['source'] == 'unidic')
        self.assertEqual(resolver.resolve(unidic_word['text'])[0]['source'], 'unidic')
        self.assertEqual(calls, [])
        unknown = resolver.resolve('ハシゲーム')[0]
        self.assertEqual(unknown['source'], 'tdmelodic')
        self.assertEqual(unknown['pitch_patterns'], [[1, 2, 1, 1, 1]])
        self.assertEqual(unknown['accents'], [])
        self.assertTrue(unknown['estimated'])
        self.assertEqual(calls, ['ハシゲーム'])
        # 推定語も、出題用の語彙に登録せずに正解判定へ渡せる。
        self.catalog.resolver = resolver
        try:
            result = self.catalog.guess(Guess(target_id=self.word('優位')['id'], text='ハシゲーム'))
            self.assertEqual(result['answer']['source'], 'tdmelodic')
        finally:
            self.catalog.resolver = AccentResolver()

    def test_final_accent(self):
        self.assertEqual(self.word('橋')['accents'], [2])
        self.assertEqual(self.word('端')['accents'], [0])
        self.assertTrue(self.catalog.guess(Guess(target_id=self.word('橋')['id'], text='端', homophones=True))['correct'])
        self.assertFalse(self.catalog.guess(Guess(target_id=self.word('橋')['id'], text='端', homophones=False))['correct'])

    def test_recent_word(self):
        result = self.catalog.guess(Guess(target_id=self.word('優位')['id'], text='周囲', recent=[self.word('周囲')['key']]))
        self.assertFalse(result['correct'])

    def test_homophone_option(self):
        pair = next((a, b) for group in self.catalog.readings.values() for a in group for b in group
                    if a['key'] != b['key'] and set(a['accents']) & set(b['accents']) and a['text'] != b['text'] and any('一' <= c <= '龥' for c in b['text']))
        a, b = pair
        self.assertFalse(self.catalog.guess(Guess(target_id=a['id'], text=b['text']))['correct'])
        self.assertTrue(self.catalog.guess(Guess(target_id=a['id'], text=b['text'], homophones=True))['correct'])
        self.assertFalse(self.catalog.guess(Guess(target_id=a['id'], text=a['reading'], homophones=True))['correct'])

    def test_omitted_reading_in_kanjium(self):
        for text, reading, accents in [('サーバー', 'サーバー', [1]),
                                       ('スパゲッティ', 'スパゲッティ', [3]),
                                       ('おっ', 'オッ', [0, 1])]:
            word = self.catalog.resolver.resolve(text)[0]
            self.assertEqual(word['source'], 'kanjium')
            self.assertEqual(word['reading'], reading)
            self.assertEqual(word['accents'], accents)

    def test_shiika_sepia_regression(self):
        target = next(w for w in self.catalog.words.values()
                      if w['text'] == '詩歌' and w['reading'] == 'シイカ')
        result = self.catalog.guess(Guess(target_id=target['id'], text='セピア'))
        self.assertTrue(result['correct'])
        self.assertEqual(result['answer']['source'], 'kanjium')
        self.assertEqual(result['answer']['reading'], 'セピア')
        self.assertEqual(result['answer']['accents'], [1])

    def test_invalid_kanjium_result_falls_through(self):
        resolver = AccentResolver(predictor=lambda text, reading: [1, 2, 1, 1, 1])
        resolver.surfaces['大阪'] = [('大阪', '', [100])]
        self.assertEqual(resolver.resolve('大阪')[0]['source'], 'unidic')
        resolver.surfaces['ハシゲーム'] = [('ハシゲーム', '', [100])]
        self.assertEqual(resolver.resolve('ハシゲーム')[0]['source'], 'tdmelodic')

    def test_prediction_failure_is_explicit(self):
        def fail(text, reading):
            raise ValueError('unsupported model input')
        resolver = AccentResolver(predictor=fail)
        with self.assertLogs('accents', level='ERROR'):
            with self.assertRaises(HTTPException) as failure:
                resolver.resolve('ハシゲーム')
        self.assertEqual(failure.exception.status_code, 422)

    def test_kanjium_target_pool(self):
        self.assertGreater(len(self.catalog.target_ids), 50000)
        for ident in self.catalog.target_ids:
            self.assertEqual(self.catalog.words[ident]['source'], 'kanjium')
        # 各難易度でも小さな固定リストに限定されていないことを確認。
        for low, high in [(2, 3), (4, 5), (6, 8)]:
            pool = [w for ident, w in self.catalog.words.items()
                    if ident in self.catalog.target_ids and low <= w['mora_count'] <= high]
            self.assertGreater(len(pool), 1000)

    def test_same_spelling_with_different_reading(self):
        for w in self.catalog.words.values():
            if w['text'] == '端':
                result = self.catalog.guess(Guess(target_id=w['id'], text='端', homophones=True))
                self.assertFalse(result['correct'])

    def test_frequency_filtered_targets(self):
        self.assertGreater(len(self.catalog.common_target_ids), 1000)
        self.assertLess(len(self.catalog.common_target_ids), len(self.catalog.target_ids))
        for difficulty in ['easy', 'normal', 'hard']:
            for _ in range(5):
                word = self.catalog.target(Rules(difficulty=difficulty))
                self.assertLessEqual(self.catalog.frequency_ranks[normalize(word['text'])], MAX_TARGET_FREQUENCY_RANK)
                self.assertEqual(word['source'], 'kanjium')

    def test_solvable_targets(self):
        for difficulty in ['easy', 'normal', 'hard']:
            rules = Rules(difficulty=difficulty)
            target = self.catalog.target(rules)
            self.assertTrue(any(self.catalog.alternatives(target, rules)))


if __name__ == '__main__':
    unittest.main()
