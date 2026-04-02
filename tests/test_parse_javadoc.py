"""
测试 Javadoc HTML 解析器
"""

import pytest
import sys
import os
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from parse_javadoc import JavadocParser


@pytest.fixture
def parser():
    """创建解析器实例"""
    return JavadocParser(encoding="gb2312")


@pytest.fixture
def sample_html_path():
    """样本 HTML 文件路径"""
    return Path(__file__).parent / "fixtures" / "sample_class.html"


class TestJavadocParser:
    """测试 JavadocParser 类"""

    def test_init(self):
        """测试解析器初始化"""
        parser = JavadocParser()
        assert parser.encoding == "gb2312"

        parser_utf8 = JavadocParser(encoding="utf-8")
        assert parser_utf8.encoding == "utf-8"

    def test_parse_file(self, parser, sample_html_path):
        """测试解析单个文件"""
        result = parser.parse_file(sample_html_path)

        # 验证基本结构
        assert "class" in result
        assert "package" in result
        assert "full_class" in result
        assert "file" in result
        assert "methods" in result

    def test_extract_class_name(self, parser, sample_html_path):
        """测试提取类名"""
        result = parser.parse_file(sample_html_path)
        assert result["class"] == "AddressDictionary"

    def test_extract_package_name(self, parser, sample_html_path):
        """测试提取包名"""
        result = parser.parse_file(sample_html_path)
        assert result["package"] == "com.supermap.analyst.addressmatching"

    def test_full_class_name(self, parser, sample_html_path):
        """测试完整类名"""
        result = parser.parse_file(sample_html_path)
        expected = "com.supermap.analyst.addressmatching.AddressDictionary"
        assert result["full_class"] == expected

    def test_extract_methods(self, parser, sample_html_path):
        """测试提取方法列表"""
        result = parser.parse_file(sample_html_path)
        methods = result["methods"]

        # 应该有 5 个方法
        assert len(methods) == 5

        # 验证方法名
        method_names = [m["name"] for m in methods]
        assert "connect" in method_names
        assert "getDatasource" in method_names
        assert "getVersion" in method_names
        assert "isConnected" in method_names
        assert "finalize" in method_names

    def test_method_details(self, parser, sample_html_path):
        """测试方法详情"""
        result = parser.parse_file(sample_html_path)
        methods = result["methods"]

        # 查找 connect 方法
        connect_method = next((m for m in methods if m["name"] == "connect"), None)
        assert connect_method is not None
        assert "void" in connect_method["signature"]
        assert "connect" in connect_method["signature"]
        assert "Connect to address dictionary database" in connect_method["description"]

        # 查找 getVersion 方法（静态方法）
        version_method = next((m for m in methods if m["name"] == "getVersion"), None)
        assert version_method is not None
        assert "String" in version_method["signature"]
        assert "Get version number" in version_method["description"]

    def test_parse_nonexistent_file(self, parser):
        """测试解析不存在的文件"""
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/file.html")

    def test_parse_directory(self, parser, tmp_path):
        """测试解析目录"""
        # 创建临时目录结构
        test_dir = tmp_path / "test_javadoc"
        test_dir.mkdir()

        # 复制样本文件
        sample_content = (Path(__file__).parent / "fixtures" / "sample_class.html").read_text(encoding="gb2312")

        # 创建多个测试文件
        (test_dir / "ClassA.html").write_text(sample_content, encoding="gb2312")
        (test_dir / "ClassB.html").write_text(sample_content, encoding="gb2312")

        sub_dir = test_dir / "subpackage"
        sub_dir.mkdir()
        (sub_dir / "ClassC.html").write_text(sample_content, encoding="gb2312")

        # 解析目录
        results = parser.parse_directory(test_dir)

        # 验证结果
        assert len(results) == 3

    def test_parse_directory_with_output(self, parser, tmp_path):
        """测试解析目录并输出 JSON"""
        test_dir = tmp_path / "test_javadoc"
        test_dir.mkdir()

        sample_content = (Path(__file__).parent / "fixtures" / "sample_class.html").read_text(encoding="gb2312")
        (test_dir / "TestClass.html").write_text(sample_content, encoding="gb2312")

        output_file = tmp_path / "output.json"

        results = parser.parse_directory(test_dir, output_json=str(output_file))

        assert output_file.exists()
        assert len(results) == 1

    def test_parse_directory_nonexistent(self, parser):
        """测试解析不存在的目录"""
        with pytest.raises(FileNotFoundError):
            parser.parse_directory("/nonexistent/directory")


class TestRealHTML:
    """测试真实 HTML 文件（如果存在）"""

    def test_parse_real_file(self, parser):
        """测试解析真实的 Javadoc HTML 文件"""
        real_html_path = Path("SuperMap iObjects Java Javadoc/com/supermap/realspace/AdjustColorCurveSetting.html")

        if not real_html_path.exists():
            pytest.skip("真实 HTML 文件不存在，跳过此测试")

        result = parser.parse_file(real_html_path)

        # 验证基本结构
        assert result["class"] is not None
        assert result["package"] is not None
        assert result["full_class"] is not None
        assert isinstance(result["methods"], list)

        # 验证类名
        assert result["class"] == "AdjustColorCurveSetting"
        assert result["package"] == "com.supermap.realspace"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
