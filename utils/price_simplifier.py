import re

class PriceSimplifier:
    def __init__(self):
        pass

    def simplify_price(self, text):
        if not text:
            return ""

        # 前処理
        text = text.replace("〜", "-").replace("～", "-").replace(" ", "").replace("¥", "").replace(",", "")

        # 時給・日給を除外
        if any(kw in text for kw in ["時給", "日給"]):
            return ""

        # 範囲マッチ (例: 1500万-1800万円, 60000-80000円)
        range_pattern = re.compile(r'(?P<low>\d+)[^\d-]*-(?P<high>\d+)(?P<unit>万|万円|円)?')
        match = range_pattern.search(text)
        if match:
            low = int(match.group("low"))
            high = int(match.group("high"))
            unit = match.group("unit")

            if unit == "円" or unit is None:
                low //= 10000
                high //= 10000
            # 万・万円はそのまま
            return f"{low}-{high}万"

        # 単体金額マッチ
        single_pattern = re.compile(r'(\d+)(万|万円|円)?')
        match = single_pattern.search(text)
        if match:
            value = int(match.group(1))
            unit = match.group(2)

            if unit == "円" or unit is None:
                value = value // 10000
            # 万・万円の場合はそのまま
            return f"{value}万"

        return ""

# テストコード
if __name__ == "__main__":
    test_cases = [
        ("月額10万円〜200万円（経験に応じて応相談）", "10-200万"),
        ("¥500,000", "50万"),
        ("200万-300万", "200-300万"),
        ("800000円", "80万"),
        ("面談", ""),
        ("時給5000円", ""),
        ("年俸1500万〜1800万円", "1500-1800万"),
        ("月給80万円", "80万"),
        ("要相談", ""),
        ("15000円", "1万"),
        ("給与: 100万円 + インセンティブ", "100万"),
        ("給与範囲: 50万-80万円", "50-80万"),
        ("月額50万円(能力に応じて優遇)", "50万"),
        ("日給8000円", ""),
        ("1万円", "1万"),
        ("9999万円", "9999万"),
        ("給与50000円", "5万"),
        ("60000-80000円", "6-8万"),
        ("給与: 1,200,000円", "120万"),
    ]

    print("=== 価格解析器テスト ===")
    price_simplifier = PriceSimplifier()  # インスタンス化
    for text, expected in test_cases:
        result = price_simplifier.simplify_price(text)  # メソッド呼び出し
        icon = "✅" if result == expected else "❌"
        print(f"{icon} 入力: {text:<40} 出力: {result:<12} 予期される: {expected}")
