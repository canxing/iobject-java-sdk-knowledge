#!/usr/bin/env node
/**
 * SDK Knowledge Base Search Script
 * 零依赖 Node.js 脚本，直接调用远程 API 进行语义搜索
 */

const API_BASE_URL = process.env.SDK_API_URL || 'http://172.27.16.134:8000';

async function search(query, topK = 5) {
  if (!query) {
    console.error('错误：请提供查询内容');
    console.error('用法：node search.js "查询内容" [top_k]');
    process.exit(1);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const results = data.results || [];

    if (results.length === 0) {
      console.log(`未找到与 '${query}' 相关的 API`);
      return;
    }

    const lines = [`# SDK API 搜索结果`, `查询: \`${query}\`\n`, `找到 ${results.length} 个相关 API:\n`];

    for (let i = 0; i < results.length; i++) {
      const r = results[i];
      lines.push(`## ${i + 1}. ${r.class}.${r.method}`);
      lines.push(`**相似度**: ${(r.similarity * 100).toFixed(1)}%`);
      lines.push(`**签名**: \`${r.signature}\``);
      if (r.description) {
        lines.push(`**描述**: ${r.description}`);
      }
      lines.push('');
    }

    console.log(lines.join('\n'));
  } catch (error) {
    if (error.code === 'ECONNREFUSED' || error.cause?.code === 'ECONNREFUSED') {
      console.error(`错误：无法连接到 SDK API 服务 (${API_BASE_URL})`);
      console.error('请确保远程服务已启动');
    } else {
      console.error(`查询出错: ${error.message}`);
    }
    process.exit(1);
  }
}

const query = process.argv[2];
const topK = parseInt(process.argv[3], 10) || 5;

search(query, topK);
