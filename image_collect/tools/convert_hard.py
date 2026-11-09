"""정연 R_hard 의 meta.csv 를 데이터 명세 형식으로 바꾼다. 라벨 내용은 바꾸지 않고 값 이름만 옮긴다.

바꾸는 것
  image_id = rhard_ + SHA-1 앞 16자리, file = images/<image_id>.<확장자>
  label: 합법 광고 -> legal_ad, 계도 -> campaign
  site_type: 사이트 기준 초안 (아래 SITE_TYPE). 정연이 확인할 값이다
  render_w, render_h: 명세대로 비움 (x, y, selector 도 빈 칸)
  link_href: page_url 과 같은 행은 비움
  collected_at: 한국 시간 표시 +09:00 추가
  열 추가: set, element, x, y, selector, alt, lang, subtype, note, labeler

사용: python tools/convert_hard.py <정연 meta.csv> <출력 meta_hard.csv> [--images <collected 폴더> --out-images <images 폴더>]
"""
import argparse
import os
import shutil

import pandas as pd

LABEL = {"합법 광고": "legal_ad", "계도": "campaign"}
SITE_TYPE = {
    "ngcc.go.kr": "campaign_org", "kcgp.or.kr": "campaign_org", "police.go.kr": "campaign_org",
    "lepopark.or.kr": "public", "korea.kr": "public", "gne.go.kr": "public", "kspo.or.kr": "public",
    "jbe.go.kr": "public", "gmyouth.or.kr": "public", "gg.go.kr": "public", "goe.go.kr": "public",
    "jje.go.kr": "public", "mcst.go.kr": "public", "mentalhealth.go.kr": "public", "ulsan.go.kr": "public",
    "sportstoto.co.kr": "lottery", "withtoto.co.kr": "lottery", "betman.co.kr": "lottery", "dhlottery.co.kr": "lottery",
    "hanabank.com": "finance", "wooribank.com": "finance", "kbstar.com": "finance",
    "kuh.ac.kr": "hospital", "dkuh.co.kr": "hospital", "ajoumc.or.kr": "hospital", "samsunghospital.com": "hospital",
    "eumc.ac.kr": "hospital", "amc.seoul.kr": "hospital", "hyumc.com": "hospital",
    "smarttoday.co.kr": "news", "osen.co.kr": "news", "daum.net": "news", "fsnews.co.kr": "news",
    "hankyung.com": "news", "isplus.com": "news", "hangyo.com": "news", "sidae.com": "news",
    "thinkyou.co.kr": "other", "linkareer.com": "other", "contestkorea.com": "other", "apps.apple.com": "other",
}
COLS = ["image_id", "set", "file", "sha1", "source_url", "page_url", "site", "site_type", "element", "w", "h",
        "render_w", "render_h", "x", "y", "selector", "link_href", "alt", "lang", "collected_at",
        "label", "subtype", "unsure", "note", "labeler"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta")
    ap.add_argument("out")
    ap.add_argument("--images", default="")
    ap.add_argument("--out-images", default="")
    a = ap.parse_args()
    m = pd.read_csv(a.meta, dtype=str, encoding="utf-8-sig").fillna("")
    unknown = sorted(set(m["site"]) - set(SITE_TYPE))
    if unknown:
        raise SystemExit(f"site_type 표에 없는 사이트: {unknown}")
    bad = sorted(set(m["label"]) - set(LABEL))
    if bad:
        raise SystemExit(f"옮길 수 없는 라벨: {bad}")
    ext = m["file"].str.rsplit(".", n=1).str[-1].str.lower()
    m["image_id_old"] = m["image_id"]
    m["image_id"] = "rhard_" + m["sha1"].str[:16]
    src = m["file"]
    m["file"] = "images/" + m["image_id"] + "." + ext
    m["set"] = "R_hard"
    m["label"] = m["label"].map(LABEL)
    m["site_type"] = m["site"].map(SITE_TYPE)
    m["link_href"] = m["link_href"].where(m["link_href"] != m["page_url"], "")
    m["collected_at"] = m["collected_at"] + "+09:00"
    for c in ["element", "render_w", "render_h", "x", "y", "selector", "alt", "lang", "subtype", "note"]:
        m[c] = ""
    m["labeler"] = "정연"
    m[COLS].to_csv(a.out, index=False, encoding="utf-8")
    m[["image_id_old", "image_id"]].to_csv(os.path.splitext(a.out)[0] + "_id_map.csv", index=False, encoding="utf-8")
    print("행", len(m), "라벨", m["label"].value_counts().to_dict(), "link_href 남음", int((m["link_href"] != "").sum()))
    if a.images and a.out_images:
        os.makedirs(a.out_images, exist_ok=True)
        for s, new in zip(src, m["file"]):
            shutil.copyfile(os.path.join(a.images, os.path.basename(s)), os.path.join(a.out_images, os.path.basename(new)))
        print("이미지 복사", len(m))


if __name__ == "__main__":
    main()
