# -*- coding: utf-8 -*-
"""PDF 에서 글자를 뽑아낸다.

**표를 복원하지 않는다.** PDF 는 사람 눈에 보기 좋게 그리는 형식이라
어디까지가 표의 한 칸인지가 파일에 적혀 있지 않다. 기본 추출을 쓰면 표의
행과 열이 무너지고, 그림 안에 들어 있는 표는 **아예 한 글자도 나오지 않는다.**
그 결과를 그대로 보여 주는 것이 이 단계의 교보재다. 표 추출기를 붙이면
2교시가 성립하지 않는다.

손상을 어떻게 짚어 주는가:
  줄 단위로 "이 줄은 표가 깨진 자리"를 판정하려 했더니 목차의 `5.2.1. H.263`
  같은 줄이 전부 걸렸다. 숫자 비중만으로는 표와 목차를 가를 수 없다.
  그래서 **페이지 단위**로 본다. 글자가 거의 안 나온 페이지는 그 자리에
  그림이나 이미지로 된 표가 있었다는 뜻이고, 이건 오판할 여지가 없다.
"""

from pypdf import PdfReader

# 이 글자 수보다 적게 나온 페이지는 "글자가 거의 없는 페이지"로 본다.
THIN_PAGE_CHARS = 120


def parse_pdf(path):
    """→ {pages, text, n_pages, n_chars, thin_pages, empty_pages}"""
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception:                      # noqa: BLE001 — 깨진 페이지도 넘어간다
            text = ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        pages.append({"page": i, "text": text, "n_chars": len(text.strip())})

    full = "\n".join(p["text"] for p in pages)
    thin = [p["page"] for p in pages if p["n_chars"] < THIN_PAGE_CHARS]
    empty = [p["page"] for p in pages if p["n_chars"] == 0]
    return {
        "pages": pages,
        "text": full,
        "n_pages": len(pages),
        "n_chars": len(full),
        "thin_pages": thin,
        "empty_pages": empty,
    }


def is_thin(page):
    return page["n_chars"] < THIN_PAGE_CHARS


def page_of(pages, offset):
    """전체 텍스트의 문자 위치 → 그 위치가 속한 원본 페이지 번호."""
    run = 0
    for p in pages:
        run += len(p["text"]) + 1              # join 에 쓴 개행 1
        if offset < run:
            return p["page"]
    return pages[-1]["page"] if pages else 0
