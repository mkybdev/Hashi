## TODO

- 開発者（あるいはプレイヤーも）が語彙を追加したり、誤ったアクセントを修正したりできるようにしたいです。とりあえず tdmelodic の推論結果を元にデータベースを構築し、フロントエンドの専用画面から語彙を追加リクエストしたり、プレイ中にアクセントの誤りがあればその場で修正リクエストをする、と言った形です。
- 読みを正しく取得するようにする
- **単語データベースの拡張 (Phase 2)**: UniDic CSVソースファイルをNINJALからダウンロードし、名詞を抽出してデータベースに追加する（現在約70語→目標10,000-20,000語）
    - https://tdmelodic.readthedocs.io/ja/latest/pages/unidic-dicgen.html に従ってアクセント辞書を生成し、https://tdmelodic.readthedocs.io/ja/latest/pages/unidic-usage.html に従って MeCab 辞書として利用することも考えられる
