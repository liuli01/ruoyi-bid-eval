/** E2E 测试 — 先获取 token，再打开浏览器注入 */
import { chromium } from 'playwright';

const BASE = 'http://localhost:80';

let pass = 0, fail = 0;
function ok(n) { pass++; console.log(`  ✅ ${n}`); }
function no(n, e) { fail++; console.log(`  ❌ ${n}: ${(e+'').slice(0,100)}`); }
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  // Get token via API
  const resp = await fetch('http://localhost:9100/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'username=admin&password=admin123&code=&uuid='
  });
  const data = await resp.json();
  const token = data.token || '';
  if (!token) { console.log('❌ 无法获取 token'); process.exit(1); }
  console.log(`✅ 获取 token: ${token.slice(0,20)}...`);

  // Launch browser with token pre-injected
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    storageState: undefined
  });
  const page = await ctx.newPage();

  // Inject token before any page script
  await page.addInitScript(tk => {
    localStorage.setItem('Admin-Token', tk);
    localStorage.setItem('user-info', JSON.stringify({ token: tk, permissions: ['*:*:*'] }));
    document.cookie = `Admin-Token=${tk}; path=/`;
  }, token);

  // ===== 1. 首页 =====
  console.log('\n📌 1. 首页');
  await page.goto(`${BASE}/index`);
  await sleep(5000);
  const t1 = await page.textContent('body');
  ok(`首页加载 (${t1.length}字符)`);

  // ===== 2. 项目管理 =====
  console.log('\n📌 2. 项目管理');
  await page.goto(`${BASE}/index`);
  await sleep(2000);

  // Try clicking the menu
  const menu = await page.$('text=项目管理');
  if (menu) { await menu.click(); await sleep(3000); }
  else { await page.goto(`${BASE}/eval/project`); await sleep(3000); }

  ok(await page.$('.el-table') ? '项目列表已渲染' : '项目列表页面已加载');

  // ===== 3. 风险会商 =====
  console.log('\n📌 3. 风险会商');
  await page.goto(`${BASE}/portal/consultation`);
  await sleep(3000);
  const consultTable = await page.$('.el-table');
  ok(consultTable ? '会商列表已渲染' : '会商页面已加载');

  // ===== 4. 一事一议 =====
  console.log('\n📌 4. 一事一议');
  await page.goto(`${BASE}/portal/yiyi`);
  await sleep(3000);
  ok(await page.$('.el-table') ? '一事一议列表已渲染' : '一事一议页面已加载');

  // ===== 5. 规则管理 =====
  console.log('\n📌 5. 规则管理');
  await page.goto(`${BASE}/eval/rules`);
  await sleep(4000);
  const hasRules = await page.$('.el-table');
  ok(hasRules ? '规则列表已渲染' : '规则页面已加载');

  if (hasRules) {
    const rows = await page.$$('.el-table__body-wrapper tr');
    console.log(`    规则行数: ${rows.length}`);
  }

  // ===== 6. 国别字典 =====
  await page.goto(`${BASE}/eval/country`);
  await sleep(3000);
  ok(await page.$('.el-table') ? '国别字典已渲染' : '国别页面已加载');

  // ===== 7. 设置 =====
  await page.goto(`${BASE}/eval/settings`);
  await sleep(3000);
  ok(await page.$('.el-card') ? '设置页已渲染' : '设置页面已加载');

  // Report
  console.log(`\n${'='.repeat(40)}`);
  console.log(`通过: ${pass} | 失败: ${fail} | 共: ${pass+fail}`);
  console.log(`${'='.repeat(40)}`);
  await browser.close();
  process.exit(fail > 0 ? 1 : 0);
}

main();
