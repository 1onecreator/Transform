import re, sys
from typing import Optional

CN_DASHES = r"[－—–-]"

def clean(s):
    return (s or "").strip()

def pages_piece(p: str) -> str:
    if not p:
        return ""
    p = re.sub(CN_DASHES, "-", p)
    p = re.sub(r"\s+", "", p)
    return f"第{p}页"

def date_cn(iso: str) -> str:
    iso = iso.strip().rstrip(".")
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", iso)
    if m:
        y, m1, d = map(int, m.groups())
        return f"{y}年{m1}月{d}日"
    m = re.match(r"(\d{4})-(\d{1,2})", iso)
    if m:
        y, m1 = map(int, m.groups())
        return f"{y}年{m1}月"
    m = re.match(r"(\d{4})", iso)
    if m:
        return f"{int(m.group(1))}年"
    return iso

# 统一标点符号为半角符号
def normalize_punct(s: str) -> str:
    table = {
        "，": ",", "。": ".", "：": ":", "；": ";",
        "（": "(", "）": ")", "［": "[", "］": "]",
        "—": "-", "－": "-", "–": "-",
        "、": ",",
    }
    for k, v in table.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# 忽略 DOI
def preclean_tail(s: str) -> str:
    s = re.sub(r'\s*DOI\s*[:：]\s*\S+\.?\s*$', "", s, flags=re.IGNORECASE)
    return s

#保留行首序号
def extract_leading_index(s: str):
    s = s.lstrip()
    m = re.match(r'^\[\s*\d+\s*\]', s)
    if m:
        prefix = m.group(0)          # 如 "[1]"
        remainder = s[m.end():].lstrip()
        return prefix, remainder
    return "", s

class GB2YLSConverter:
    #书籍
    def book(self, s: str) -> Optional[str]:
        s = preclean_tail(s.strip())
        p1 = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\[]+)\[M\]\.\s*'
            r'(?P<place>[^:]+):\s*'
            r'(?P<publisher>[^,:]+)\s*[,:\s]\s*'
            r'(?P<year>\d{4})(?:\d{2})?\s*'
            r'(?::\s*(?P<pages>\d+(?:\s*' + CN_DASHES + r'\s*\d+)?))?\.?\s*$'
        )
        p2 = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\[]+)\[M\]\.\s*'
            r'(?P<publisher>[^,:]+)\s*[,:\s]\s*'
            r'(?P<year>\d{4})(?:\d{2})?\s*'
            r'(?::\s*(?P<pages>\d+(?:\s*' + CN_DASHES + r'\s*\d+)?))?\.?\s*$'
        )
        p3 = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\.]+)\.\s*'
            r'(?P<place>[^:]+):\s*'
            r'(?P<publisher>[^,:]+)\s*[,:\s]\s*'
            r'(?P<year>\d{4})(?:\d{2})?\.?\s*$'
        )
        for p in (p1, p2, p3):
            m = re.match(p, s)
            if m:
                g = m.groupdict()
                author, title = clean(g.get("author")), clean(g.get("title"))
                publisher = clean(g.get("publisher"))
                year = clean(g.get("year"))[:4]
                pages = clean(g.get("pages"))
                pages_pieces = "，" + pages_piece(pages) if pages else ""
                return f"{author}:《{title}》，{publisher}{year}年版{pages_pieces}。"
        return None

    #期刊
    def journal(self, s: str) -> Optional[str]:
        s = preclean_tail(s.strip())
        p1 = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\[]+)\[J\]\.\s*'
            r'(?P<journal>[^,]+),\s*'
            r'(?P<year>\d{4}),\s*'
            r'(?P<volume>\d+)\('
            r'(?P<issue>\d+)\):\s*'
            r'(?P<pages>\d+(?:\s*' + CN_DASHES + r'\s*\d+)?)\.?\s*$'
        )
        p2 = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\[]+)\[J\]\.\s*'
            r'(?P<journal>[^,]+),\s*'
            r'(?P<year>\d{4})\('
            r'(?P<issue>\d+)\):\s*'
            r'(?P<pages>\d+(?:\s*' + CN_DASHES + r'\s*\d+)?)\.?\s*$'
        )
        p3 = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\[]+)\[J\]\.\s*'
            r'(?P<journal>[^,]+),\s*'
            r'(?P<year>\d{4})\('
            r'(?P<issue>\d+)\)\.?\s*$'
        )
        for p in (p1, p2, p3):
            m = re.match(p, s)
            if m:
                g = m.groupdict()
                author = clean(g["author"]); title = clean(g["title"])
                journal = clean(g["journal"]); year = clean(g["year"])
                issue = clean(g.get("issue")); pages = clean(g.get("pages"))
                issue_piece = f"第{issue}期" if issue else ""
                pages_piece_str = "，" + pages_piece(pages) if pages else ""
                return f"{author}:《{title}》，载《{journal}》{year}年{issue_piece}{pages_piece_str}。"
        return None

    #网络文章
    def online(self, s: str) -> Optional[str]:
        s = preclean_tail(s.strip())
        p1a = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\[]+)\[EB/OL\]\.\s*'
            r'(?P<site>[^,]+),\s*'
            r'(?P<date>\d{4}(?:-\d{2}(?:-\d{2})?)?)'
            r'(?:\((?P<acc1>\d{4}(?:-\d{2}(?:-\d{2})?)?)\))?'
            r'\.\s*(?P<url>https?://[^\s,]+)\s*\.?\s*$'
        )
        p1b = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\[]+)\[EB/OL\]\.\s*'
            r'(?P<site>[^,]+),\s*'
            r'(?P<date>\d{4}(?:-\d{2}(?:-\d{2})?)?)'
            r'\.\s*(?P<url>https?://[^\s,]+)\s*,\s*'
            r'(?P<acc2>\d{4}(?:-\d{2}(?:-\d{2})?)?)\s*\.?\s*$'
        )
        p2a = (
            r'^(?P<site>[^\.]+)\[EB/OL\]\.\s*'
            r'(?P<site2>[^,]+),\s*'
            r'(?P<date>\d{4}(?:-\d{2}(?:-\d{2})?)?)'
            r'(?:\((?P<acc1>\d{4}(?:-\d{2}(?:-\d{2})?)?)\))?'
            r'\.\s*(?P<url>https?://[^\s,]+)\s*\.?\s*$'
        )
        p2b = (
            r'^(?P<site>[^\.]+)\[EB/OL\]\.\s*'
            r'(?P<site2>[^,]+),\s*'
            r'(?P<date>\d{4}(?:-\d{2}(?:-\d{2})?)?)'
            r'\.\s*(?P<url>https?://[^\s,]+)\s*,\s*'
            r'(?P<acc2>\d{4}(?:-\d{2}(?:-\d{2})?)?)\s*\.?\s*$'
        )

        for pat, author_mode in ((p1a, True), (p1b, True), (p2a, False), (p2b, False)):
            m = re.match(pat, s)
            if not m:
                continue
            g = m.groupdict()
            site = clean(g.get("site"))
            title = clean(g.get("title")) if author_mode else ""
            author = clean(g.get("author")) if author_mode else ""
            pub = date_cn(clean(g.get("date")))
            acc = clean(g.get("acc1") or g.get("acc2"))
            acc_cn = f"（{date_cn(acc)}）" if acc else ""
            url = clean(g.get("url"))

            if author_mode:
                return f"{author}:《{title}》，载{site}{pub}{acc_cn}。{url}。"
            else:
                site2 = clean(g.get("site2"))
                name = site2 or site
                return f"参见{name}{pub}{acc_cn}。{url}。"

        return None

    #学位论文
    def thesis(self, s: str) -> Optional[str]:
        s = preclean_tail(s.strip())
        p = (
            r'^(?P<author>[^\.]+)\.\s*'
            r'(?P<title>[^\[]+)\[D(?:/OL)?\]\.\s*'
            r'(?:(?P<place>[^:]+):\s*)?' 
            r'(?P<school>[^,，\.]+)\s*[,，\.]?\s*'
            r'(?P<year>\d{4})(?:\.)?\s*$'
        )
        m = re.match(p, s)
        if m:
            g = m.groupdict()
            author = clean(g['author'])
            title = clean(g['title'])
            school = clean(g['school'])
            year = clean(g['year'])
            return f"{author}:《{title}》，{school}{year}年学位论文。"
        return None

    #法规
    def legal(self, s: str) -> Optional[str]:
        s = preclean_tail(s.strip())
        pA = (
            r'^[《"]?(?P<title>[^》"\[\(]+)[》"]?\s*'
            r'[\[\(（]\s*(?P<typ>S|Z)\s*[\]\)）]\.\s*'
            r'(?:(?P<src>[^,]+),\s*)?'
            r'(?P<date>\d{4}(?:-\d{2}(?:-\d{2})?)?)\.?\s*$'
        )
        pB = (
            r'^(?P<src>[^\.]+)\.\s*'
            r'(?P<title>[^ \[\(]+)\s*'
            r'[\[\(（]\s*(?P<typ>S|Z)\s*[\]\)）]\.\s*'
            r'(?P<date>\d{4}(?:-\d{2}(?:-\d{2})?)?)\.?\s*$'
        )
        for p in (pB, pA):
            m = re.match(p, s)
            if m:
                g = m.groupdict()
                title = clean(g['title'])
                src = clean(g.get('src'))
                date = date_cn(clean(g['date']))
                if src:
                    return f"《{title}》，{src}，{date}发布。"
                else:
                    return f"《{title}》，{date}发布。"
        return None

    #司法案例
    def case(self, s: str) -> Optional[str]:
        s = preclean_tail(s.strip())
        p_date = (
            r'^(?P<name>[^\[]+)\[(?i:z)\]\.\s*' 
            r'(?P<court>[^,]+),\s*'
            r'(?P<date>\d{4}(?:-\d{2}(?:-\d{2})?)?)\.?\s*$'
        )
        p_case_no = (
            r'^(?P<name>[^\[]+)\[(?i:z)\]\.\s*'
            r'(?P<court>[^,]+),\s*'
            r'(?P<doc>.+?)\.?\s*$'
        )

        m = re.match(p_date, s)
        if m:
            g = m.groupdict()
            return f"{clean(g['name'])}，{clean(g['court'])}{date_cn(clean(g['date']))}。"

        m = re.match(p_case_no, s)
        if m:
            g = m.groupdict()
            return f"{clean(g['name'])}，{clean(g['court'])}{clean(g['doc'])}。"

        return None

    #判定
    def convert_auto(self, s: str) -> str:
        s = normalize_punct(s)
        prefix, body = extract_leading_index(s)
        s = body
        for h in (self.thesis, self.book, self.journal, self.online, self.legal, self.case):
            out = h(s)
            if out:
                return (prefix + " " if prefix and not prefix.endswith(" ") else prefix) + out
        return (prefix + " " if prefix and not prefix.endswith(" ") else prefix) + f"无法解析（未知类型）。原文：{s}"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GB/T -> 法学引注")
    parser.add_argument("--auto", action="store_true", help="从stdin读取多行进行转换")
    args = parser.parse_args()
    conv = GB2YLSConverter()
    if args.auto and not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            print(conv.convert_auto(line))
        return
    while True:
        try:
            s = input("\n粘贴一条国标格式：\n> ").strip()
            if s.lower() in {"q","quit","exit"}:
                print("已退出。"); break
            print("转换结果：\n" + conv.convert_auto(s))
        except KeyboardInterrupt:
            print("\n已退出。"); break

if __name__ == "__main__":
    main()
