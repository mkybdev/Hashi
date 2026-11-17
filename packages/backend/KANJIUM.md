# Kanjium アクセントデータ

出典: https://github.com/mifunetoshiro/kanjium
原本: `data/source_files/raw/accents.txt`
固定コミットは親リポジトリが記録するサブモジュールのコミットを参照。データはサブモジュール内の`data/source_files/raw/`を直接参照します。
形式: 表記、ひらがな読み、アクセント核位置（カンマ区切り）。0は平板。

アクセント表記などの追加・修正は、Uros O. が提供する無料データベースに由来します。
The pitch accent notation, verb particle data, phonetics, homonyms and other additions or modifications to EDICT, KANJIDIC or KRADFILE were provided by Uros O. through his free database.

CC BY-SA 4.0。ライセンス全文は`vendor/kanjium/LICENSE.txt`を参照。
上流に含まれるEDICT / KANJIDIC / KRADFILEの権利はEDRDGに帰属します。
https://www.edrdg.org/edrdg/licence.html

## 頻度データ

`novels_freq.txt`も同じサブモジュールから参照します。原本は`data/source_files/raw/novels_freq.txt`。約5,000冊の小説の表記別出現回数で、一般的な親しみやすさや、各読みの頻度を保証するものではありません。頻度データ内の出典URLも原本の先頭行に保持しています。
