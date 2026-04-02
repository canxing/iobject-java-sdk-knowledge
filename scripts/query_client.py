#!/usr/bin/env python3
"""
SDK 知识库 CLI 查询客户端

命令行工具，用于查询 SDK 知识库 API
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

import requests


# 配置
DEFAULT_API_URL = "http://localhost:8000"
API_BASE_URL = os.getenv("SDK_API_URL", DEFAULT_API_URL)


def search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    调用 API 搜索

    Args:
        query: 搜索查询文本
        top_k: 返回结果数量

    Returns:
        API 响应的字典

    Raises:
        SystemExit: 当请求失败时
    """
    url = f"{API_BASE_URL}/search"
    payload = {"query": query, "top_k": top_k}

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError as e:
        print(f"错误: 无法连接到 API 服务 ({API_BASE_URL})", file=sys.stderr)
        print(f"请确保服务正在运行，或检查 SDK_API_URL 环境变量", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"错误: 请求超时", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"错误: HTTP {e.response.status_code}", file=sys.stderr)
        try:
            error_detail = e.response.json().get("detail", str(e))
            print(f"详情: {error_detail}", file=sys.stderr)
        except:
            print(f"详情: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"错误: 请求失败 - {e}", file=sys.stderr)
        sys.exit(1)


def format_results(results: Dict[str, Any]) -> str:
    """
    格式化结果为 Markdown

    Args:
        results: API 返回的结果字典

    Returns:
        格式化后的 Markdown 字符串
    """
    output = []

    # 标题
    output.append("# 搜索结果\n")

    # 获取结果列表
    result_list = results.get("results", [])
    total = results.get("total", len(result_list))

    if total == 0:
        output.append("*未找到相关结果*\n")
        return "\n".join(output)

    output.append(f"共找到 **{total}** 个相关结果\n")

    # 格式化每个结果
    for i, result in enumerate(result_list, 1):
        class_name = result.get("class", "")
        method_name = result.get("method", "")
        signature = result.get("signature", "")
        description = result.get("description", "")
        similarity = result.get("similarity", 0.0)

        # 结果标题
        output.append(f"## {i}. `{class_name}.{method_name}`")

        # 相似度（转换为百分比）
        similarity_pct = similarity * 100
        output.append(f"**相似度**: {similarity_pct:.1f}%  ")

        # 方法签名
        if signature:
            output.append(f"**签名**: `{signature}`  ")

        # 描述
        if description:
            # 清理描述中的多余空白
            desc_cleaned = " ".join(description.split())
            output.append(f"**描述**: {desc_cleaned}")

        output.append("")  # 空行分隔

    return "\n".join(output)


def check_health() -> bool:
    """
    检查 API 服务健康状态

    Returns:
        服务是否健康
    """
    url = f"{API_BASE_URL}/health"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("status") == "healthy"
    except:
        return False


def main():
    """主入口，处理命令行参数"""
    parser = argparse.ArgumentParser(
        prog="query_client.py",
        description="SDK 知识库 CLI 查询客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s "如何创建数据源"
  %(prog)s "Workspace 打开方法" --top 10
  %(prog)s "查询空间数据" --raw

环境变量:
  SDK_API_URL    API 服务地址 (默认: http://localhost:8000)
        """,
    )

    parser.add_argument(
        "query",
        type=str,
        nargs="?",
        help="自然语言查询",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=5,
        dest="top_k",
        help="返回结果数量 (默认: 5, 范围: 1-20)",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="输出原始 JSON 格式",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="检查 API 服务健康状态",
    )

    args = parser.parse_args()

    # 检查健康状态
    if args.check:
        if check_health():
            print(f"API 服务健康 ({API_BASE_URL})")
            sys.exit(0)
        else:
            print(f"API 服务不可用 ({API_BASE_URL})")
            sys.exit(1)

    # 检查查询文本
    if not args.query:
        parser.print_help()
        sys.exit(1)

    # 验证 top_k 范围
    if args.top_k < 1 or args.top_k > 20:
        print("错误: --top 必须在 1-20 范围内", file=sys.stderr)
        sys.exit(1)

    # 执行搜索
    results = search(args.query, args.top_k)

    # 输出结果
    if args.raw:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_results(results))


if __name__ == "__main__":
    main()
