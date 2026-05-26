from scholarly import scholarly, ProxyGenerator
import json
from datetime import datetime
import os
from scholarly._proxy_generator import MaxTriesExceededException


try:
    print("正在查找作者信息...")
    # Setup proxy: prefer ScraperAPI (set SCRAPER_API_KEY secret); fall back to FreeProxies for local runs.
    pg = ProxyGenerator()
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    if scraper_api_key:
        print("使用 ScraperAPI 代理...")
        success = pg.ScraperAPI(scraper_api_key)
        if not success:
            raise RuntimeError("ScraperAPI 初始化失败，请检查 SCRAPER_API_KEY 是否有效")
    else:
        print("未检测到 SCRAPER_API_KEY，回退到 FreeProxies（在 GitHub Actions 上几乎不可用）...")
        pg.FreeProxies()
    scholarly.use_proxy(pg)
    author: dict = scholarly.search_author_id(os.environ["GOOGLE_SCHOLAR_ID"])
except MaxTriesExceededException as e:
    print(f"发生异常: {e}")
else:
    print("正在填充作者详细信息...")
    scholarly.fill(author, sections=["basics", "indices", "counts", "publications"])
    # name = author["name"]
    author["updated"] = str(datetime.now())

    # 逐篇填充：单篇失败不影响整体，保留基础字段
    filled_publications = {}
    total = len(author['publications'])
    for idx, v in enumerate(author['publications'], 1):
        pub_id = v['author_pub_id']
        try:
            filled_publications[pub_id] = scholarly.fill(v)
            print(f"  [{idx}/{total}] 已填充: {pub_id}")
        except MaxTriesExceededException as e:
            print(f"  [{idx}/{total}] 填充失败，保留基础数据: {pub_id} ({e})")
            filled_publications[pub_id] = v
        except Exception as e:
            print(f"  [{idx}/{total}] 未知错误，保留基础数据: {pub_id} ({e})")
            filled_publications[pub_id] = v
    author['publications'] = filled_publications
    print(json.dumps(author, indent=2))

    print("正在创建结果目录...")
    os.makedirs("results", exist_ok=True)

    print("正在保存作者数据...")
    with open(f"results/gs_data.json", "w") as outfile:
        json.dump(author, outfile, ensure_ascii=False)

    print("正在生成 Shields.io 数据...")
    shieldio_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": f"{author.get('citedby', 0)}",
    }

    print("正在保存 Shields.io 数据...")
    with open(f"results/gs_data_shieldsio.json", "w") as outfile:
        json.dump(shieldio_data, outfile, ensure_ascii=False)

    print("数据处理完成。")
