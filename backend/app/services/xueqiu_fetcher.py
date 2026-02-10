"""
雪球数据抓取服务 - 直接抓取，不依赖 RSSHub
"""
import asyncio
import httpx
from typing import List, Dict, Optional
from datetime import datetime
import re
import json
from bs4 import BeautifulSoup


class XueqiuFetcher:
    """雪球数据直接抓取器"""

    def __init__(self):
        self.base_url = "https://xueqiu.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://xueqiu.com/",
        }

    async def fetch_user_posts(self, user_id: str, count: int = 10) -> List[Dict]:
        """
        获取用户动态

        Args:
            user_id: 用户ID
            count: 获取数量

        Returns:
            动态列表
        """
        url = f"{self.base_url}/u/{user_id}"

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                # 首先访问用户页面，获取 cookies
                print(f"正在访问用户页面: {url}")
                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    print(f"访问失败: {response.status_code}")
                    return []

                # 尝试从页面中提取数据
                soup = BeautifulSoup(response.text, 'html.parser')

                # 尝试找到包含动态数据的 script 标签
                scripts = soup.find_all('script')
                posts = []

                for script in scripts:
                    if script.string and 'SNOWFLAKE' in script.string:
                        # 提取 JSON 数据
                        try:
                            # 匹配 JSON 数据
                            pattern = r'SNOWFLAKE\s*=\s*({[^;]+});'
                            match = re.search(pattern, script.string)
                            if match:
                                data_str = match.group(1)
                                data = json.loads(data_str)

                                # 提取用户动态
                                if 'statuses' in data:
                                    for status in data['statuses'][:count]:
                                        post = self._parse_status(status, user_id)
                                        if post:
                                            posts.append(post)
                                        if len(posts) >= count:
                                            break

                                if posts:
                                    break
                        except Exception as e:
                            print(f"解析 JSON 数据失败: {e}")
                            continue

                # 如果没有找到数据，尝试解析 HTML
                if not posts:
                    posts = self._parse_html_posts(soup, user_id, count)

                print(f"成功获取 {len(posts)} 条动态")
                return posts

        except Exception as e:
            print(f"获取用户动态失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_status(self, status: Dict, user_id: str) -> Optional[Dict]:
        """解析单条动态"""
        try:
            return {
                "id": str(status.get("id", "")),
                "title": status.get("title", "")[:100],
                "content": status.get("text", status.get("description", "")),
                "author": status.get("user", {}).get("name", ""),
                "published_at": status.get("created_at", ""),
                "link": f"{self.base_url}/{status.get('id', '')}",
                "source": "xueqiu",
                "user_id": user_id,
            }
        except Exception as e:
            print(f"解析动态失败: {e}")
            return None

    def _parse_html_posts(self, soup: BeautifulSoup, user_id: str, count: int) -> List[Dict]:
        """从 HTML 中解析动态"""
        posts = []

        try:
            # 查找动态列表
            status_items = soup.find_all("div", class_="status-item")

            for item in status_items[:count]:
                try:
                    title_elem = item.find("a", class_="title")
                    content_elem = item.find("div", class_="description")
                    time_elem = item.find("span", class_="time")
                    link_elem = item.find("a", class_="title")

                    post = {
                        "id": "",
                        "title": title_elem.get_text(strip=True) if title_elem else "",
                        "content": content_elem.get_text(strip=True) if content_elem else "",
                        "author": "",
                        "published_at": time_elem.get_text(strip=True) if time_elem else "",
                        "link": link_elem.get("href", "") if link_elem else "",
                        "source": "xueqiu",
                        "user_id": user_id,
                    }

                    if post["title"] or post["content"]:
                        posts.append(post)

                except Exception as e:
                    print(f"解析单条动态失败: {e}")
                    continue

        except Exception as e:
            print(f"解析 HTML 失败: {e}")

        return posts

    async def fetch_multiple_users(self, user_configs: List[Dict], count_per_user: int = 3) -> Dict[str, List[Dict]]:
        """
        获取多个用户的动态

        Args:
            user_configs: 用户配置列表 [{"name": "但斌", "uid": "1102105103"}, ...]
            count_per_user: 每个用户获取的数量

        Returns:
            {user_name: [posts]}
        """
        results = {}

        for config in user_configs:
            name = config.get("name", "")
            uid = config.get("uid", "")

            if not uid:
                continue

            print(f"\n正在获取 {name} (UID: {uid}) 的动态...")
            posts = await self.fetch_user_posts(uid, count_per_user)
            results[name] = posts

            # 避免请求过快
            await asyncio.sleep(2)

        return results


async def main():
    """测试函数"""
    fetcher = XueqiuFetcher()

    # 测试获取但斌的动态
    print("=" * 60)
    print("测试获取但斌的动态")
    print("=" * 60)

    posts = await fetcher.fetch_user_posts("1102105103", count=5)

    if posts:
        print(f"\n成功获取 {len(posts)} 条动态:\n")
        for i, post in enumerate(posts, 1):
            print(f"【{i}】{post.get('title', '无标题')[:50]}...")
            print(f"   内容: {post.get('content', '')[:100]}...")
            print(f"   链接: {post.get('link', '')}")
            print()
    else:
        print("未能获取到动态数据")


if __name__ == "__main__":
    asyncio.run(main())
