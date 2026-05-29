"""
豆瓣电影爬虫
爬取电影数据存为 txt，供 knowledge 工具使用
"""

import requests
import time
import random
import json
import os  # 【新增】用于处理文件路径

# ========== 可调参数 ==========
# 爬取分类（豆瓣标签）
CATEGORIES = [
    "悬疑",
    "科幻",
    "爱情",
    "喜剧",
    "动作",
    "剧情",
]

# 每个分类爬多少页（每页约 20 部）
PAGES_PER_CATEGORY = 10  # 15页 ≈ 300部/分类

# 每页间隔时间（秒），防止被封
DELAY_MIN = 2
DELAY_MAX = 5

# 输出文件路径
OUTPUT_FILE = "../knowledge/douban_movies.txt"
# ===== 进度文件 =====
# 记录上次爬到的位置（分类索引 + 页码）
# 下次运行自动从断点继续，数据追加不覆盖
PROGRESS_FILE = "../knowledge/progress.json"
# =============================


# ===== 断点续爬相关函数 =====
def load_progress():
    """读取上次爬取进度"""
    try:
        with open(PROGRESS_FILE, "r") as pf:
            return json.load(pf)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"category_index": 0, "page": 0}

def save_progress(category_index, page):
    """保存当前爬取进度"""
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w") as pf:
        json.dump({"category_index": category_index, "page": page}, pf)
# ==================================

session = requests.Session()


def fetch_movies_by_tag(tag, page):
    """按标签爬取电影列表"""
    movies = []
    dic={"类型": tag}
    json_str = json.dumps(dic, ensure_ascii=False)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
        "Referer": "https://movie.douban.com/explore",
        "Origin": "https://movie.douban.com",
        "Cookie": "dbcl2=\"265832117:9JeA+bIZzKA\""
    }

    start = page * 20
    url = "https://m.douban.com/rexxar/api/v2/movie/recommend"
    params = {
        "refresh": "0",
        "start": start,
        "count": "20",
        "selected_categories": json_str,  # ← 这里放 JSON 字符串
        "tags":tag,
        "uncollect": "false"
    }
    try:
        # requests.get → session.get
        resp = session.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        items=result["items"]
        for item in items:
            if item["type"]=="movie":
                movie_id = item["id"]
                # rating 容错
                # 原来 item["rating"]["value"] 在 rating 为 None 时会报 KeyError
                # 改为 .get() 链式获取，没有评分则默认"暂无评分"
                rating = item.get("rating", {}).get("value", "暂无评分")
                info=item["card_subtitle"]
                title=item["title"]
                url1=f"https://m.douban.com/rexxar/api/v2/movie/{movie_id}/"
                try:
                    # 【修改】requests.get → session.get
                    resp1=session.get(url1, headers=headers, timeout=10)
                    data = resp1.json()
                    intro=data.get("intro","暂无简介")
                # 【修改】捕获 Exception 而不是 requests.RequestException
                # 原来只捕获网络异常，但 resp1.json() 解析失败的 JSONDecodeError 没有被捕获
                except Exception:
                    intro="暂无简介"
                time.sleep(random.uniform(2, 4))
                movies.append({
                    "title": title,
                    "rating": rating,
                    "intro": intro,
                    "info": info,
                })
            else:
                continue
    except requests.RequestException as e:
        print(f"Error fetching movies: {e}")
    print(f"[INFO] {tag} 第 {page+1}/10 页完成，本页 {len(items)} 部")
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    return movies


# save_to_txt 改为追加模式
# 原来用 'w'（覆盖写入），每次重新跑会清空之前爬到的数据
# 改为 'a'（追加写入），断点续爬时在文件末尾新增，不覆盖
def save_to_txt(movies, filepath, append=False):
    """保存为 txt 文件"""
    mode = "a" if append else "w"  # 【新增】追加模式判断
    with open(filepath, mode, encoding="utf-8") as f:
        if not append:
            f.write("# 豆瓣电影数据\n\n")
        for m in movies:
            f.write(f"## 电影名：{m['title']}\n")
            f.write(f"评分：{m['rating']}\n")
            f.write(f"信息：{m['info']}\n")
            f.write(f"简介：{m['intro']}\n\n")
    print(f"[INFO] 共 {len(movies)} 部电影，已保存到 {filepath}")


if __name__ == "__main__":
    # ===== main 逻辑，支持断点续爬 =====
    # 原来每次从第 0 个分类第 0 页开始，全部覆盖
    # 现在读取进度，从上一次停留的位置继续
    progress = load_progress()
    start_category = progress["category_index"]
    start_page = progress["page"]
    
    all_movies = []

    for cat_idx in range(start_category, len(CATEGORIES)):
        tag = CATEGORIES[cat_idx]
        first_page_of_category = 0 if cat_idx > start_category else start_page
        
        print(f"\n[INFO] 开始爬取分类：{tag}")
        
        # 每次分类单独爬并立即保存，避免进度丢失
        for page in range(first_page_of_category, PAGES_PER_CATEGORY):
            movies = fetch_movies_by_tag(tag, page=page)
            all_movies.extend(movies)
            
            # 每次爬完一页就保存到文件（追加模式），并记录进度
            # 这样即使中途中断，已爬的数据不会丢
            is_first_write = (cat_idx == 0 and page == 0 and start_category == 0)
            save_to_txt(movies, OUTPUT_FILE, append=not is_first_write)
            save_progress(cat_idx, page + 1)

    if all_movies:
        print(f"\n[OK] 爬虫完成！共 {len(all_movies)} 部电影")
        print("[INFO] 下次启动 agent 时会自动重建向量库")
    else:
        print("\n[WARN] 没有爬到数据")
    
    # ===== 爬完后删除进度文件 =====
    # 全部完成时清除进度记录
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("[INFO] 全部任务完成，已清除进度记录")
