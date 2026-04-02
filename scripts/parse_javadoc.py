"""
Javadoc HTML 解析器模块。

用于解析 SuperMap iObjects Java Javadoc HTML 文件，提取类、方法、描述等信息。
"""

import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup


class JavadocParser:
    """Javadoc HTML 文件解析器。"""

    def __init__(self, encoding="gb2312"):
        """
        初始化解析器。

        Args:
            encoding: HTML 文件编码，默认为 gb2312
        """
        self.encoding = encoding

    def parse_file(self, file_path):
        """
        解析单个 HTML 文件。

        Args:
            file_path: HTML 文件路径

        Returns:
            dict: 包含类信息的字典
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, 'r', encoding=self.encoding, errors='ignore') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        result = {
            "class": self._extract_class_name(soup),
            "package": self._extract_package_name(soup),
            "full_class": None,
            "file": str(file_path),
            "methods": self._extract_methods(soup)
        }

        # 构建完整类名
        if result["package"] and result["class"]:
            result["full_class"] = f"{result['package']}.{result['class']}"

        return result

    def _extract_class_name(self, soup):
        """
        从 HTML 中提取类名。

        Args:
            soup: BeautifulSoup 对象

        Returns:
            str: 类名
        """
        # 首先在 header div 中查找 h2 标签
        header = soup.find('div', class_='header')
        if header:
            h2 = header.find('h2', title=True)
            if h2:
                # 提取 title 属性中的类名
                title = h2.get('title', '')
                if title.startswith('Class '):
                    return title[6:]
                elif title.startswith('类 '):
                    return title[2:]
                elif title.startswith('Interface '):
                    return title[10:]
                elif title.startswith('接口 '):
                    return title[3:]

            # 备选：直接获取 h2 标签的文本内容
            h2 = header.find('h2')
            if h2:
                text = h2.get_text(strip=True)
                # 移除常见的修饰词
                for prefix in ['Class ', '类 ', 'Interface ', '接口 ', 'Enum ', '枚举 ']:
                    if text.startswith(prefix):
                        return text[len(prefix):]
                return text

        # 备选：从 title 标签提取
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            if ' ' in title_text:
                return title_text.split()[0]
            return title_text

        return None

    def _extract_package_name(self, soup):
        """
        从 HTML 中提取包名。

        Args:
            soup: BeautifulSoup 对象

        Returns:
            str: 包名
        """
        # 在 header div 中查找 subTitle
        header = soup.find('div', class_='header')
        if header:
            sub_title = header.find('div', class_='subTitle')
            if sub_title:
                return sub_title.get_text(strip=True)

        # 备选：从 package 声明中提取
        package_link = soup.find('li', string=re.compile(r'程序包'))
        if package_link:
            parent = package_link.find_parent('a')
            if parent and 'href' in parent.attrs:
                href = parent['href']
                # 从 href 解析包名
                if 'package-summary.html' in href:
                    parts = href.split('/')
                    if len(parts) > 1:
                        return '.'.join(parts[:-1])

        return None

    def _extract_methods(self, soup):
        """
        从 HTML 中提取方法列表。

        Args:
            soup: BeautifulSoup 对象

        Returns:
            list: 方法信息列表
        """
        methods = []

        # 查找方法摘要表格
        method_summary = soup.find('a', {'name': 'method.summary'})
        if method_summary:
            # 查找包含此锚点的最近的 table 元素
            # 锚点通常在 li > ul > table 结构中
            table = None
            current = method_summary
            for _ in range(10):  # 向上查找最多10层
                current = current.find_parent()
                if current is None:
                    break
                if current.name == 'table' and 'memberSummary' in current.get('class', []):
                    table = current
                    break

            # 如果没找到，尝试查找下一个 memberSummary 表格
            if not table:
                table = method_summary.find_next('table', class_='memberSummary')

            if table:
                # 遍历所有方法行（id 以 i 开头后跟数字）
                rows = table.find_all('tr', id=re.compile(r'^i\d+$'))
                for row in rows:
                    method = self._parse_method_row(row)
                    if method:
                        methods.append(method)

        return methods

    def _parse_method_row(self, row):
        """
        解析单行方法信息。

        Args:
            row: 表格行元素

        Returns:
            dict: 方法信息字典
        """
        method = {
            "name": None,
            "signature": None,
            "modifiers": None,
            "description": None
        }

        # 提取返回类型（第一列）
        col_first = row.find('td', class_='colFirst')
        if col_first:
            return_type = col_first.get_text(strip=True)
        else:
            return_type = ""

        # 提取方法名和签名（最后一列）
        col_last = row.find('td', class_='colLast')
        if col_last:
            # 查找方法名链接
            member_link = col_last.find('span', class_='memberNameLink')
            if member_link:
                link = member_link.find('a')
                if link:
                    method["name"] = link.get_text(strip=True)

            # 提取完整签名
            code_tag = col_last.find('code')
            if code_tag:
                signature = code_tag.get_text(strip=True)
                # 清理签名文本
                signature = re.sub(r'\s+', ' ', signature)

                # 将返回类型添加到签名前
                if return_type and not signature.startswith(return_type):
                    signature = f"{return_type} {signature}"

                method["signature"] = signature

                # 提取方法名（如果没有从链接获取到）
                if not method["name"]:
                    # 从签名中提取方法名
                    match = re.search(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(', signature)
                    if match:
                        method["name"] = match.group(1)

            # 提取描述
            block_div = col_last.find('div', class_='block')
            if block_div:
                method["description"] = block_div.get_text(strip=True)

        # 构建完整签名（如果没有获取到）
        if not method["signature"] and method["name"]:
            method["signature"] = f"{return_type} {method['name']}()"

        # 尝试从签名提取修饰符
        if method["signature"]:
            # 标准 Javadoc 方法摘要表格通常不显示修饰符
            # 我们尝试推断
            modifiers = []
            if 'public' in method["signature"].lower():
                modifiers.append("public")
            elif 'private' in method["signature"].lower():
                modifiers.append("private")
            elif 'protected' in method["signature"].lower():
                modifiers.append("protected")

            if 'static' in method["signature"].lower():
                modifiers.append("static")

            if modifiers:
                method["modifiers"] = ' '.join(modifiers)

        return method if method["name"] else None

    def parse_directory(self, input_dir, output_json=None):
        """
        解析整个目录中的所有 HTML 文件。

        Args:
            input_dir: 输入目录路径
            output_json: 输出 JSON 文件路径（可选）

        Returns:
            list: 所有解析结果的列表
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"目录不存在: {input_path}")

        results = []

        # 遍历所有 HTML 文件
        for html_file in input_path.rglob("*.html"):
            try:
                result = self.parse_file(html_file)
                if result["class"]:  # 只保存成功解析的类
                    results.append(result)
            except Exception as e:
                print(f"解析文件 {html_file} 时出错: {e}")

        # 如果指定了输出文件，保存为 JSON
        if output_json:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        return results


if __name__ == "__main__":
    # 示例用法
    parser = JavadocParser(encoding="gb2312")

    # 解析单个文件
    # result = parser.parse_file("SuperMap iObjects Java Javadoc/com/supermap/realspace/AdjustColorCurveSetting.html")
    # print(json.dumps(result, ensure_ascii=False, indent=2))

    # 解析整个目录
    results = parser.parse_directory(
        "SuperMap iObjects Java Javadoc",
        "data/parsed_javadoc.json"
    )
    print(f"解析完成，共 {len(results)} 个类")
