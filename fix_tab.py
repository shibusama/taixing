with open(r"D:\13191\Documents\workbuddyspace\2026-07-26-13-55-46\rocket-news\mega-projects.html","r",encoding="utf-8") as f:
    c = f.read()

# 1. Tab button
c = c.replace(
    '<button data-tab="tab-energy">&#9889; 能源动脉</button>',
    '<button data-tab="tab-energy">&#9889; 能源动脉</button>\n      <button data-tab="tab-science">&#128300; 大科学装置</button>'
)

# 2. Panel content (insert before timeline section)
panel = """    <!-- ===== Tab 4: 大科学装置 ===== -->
    <div class="tab-panel" id="tab-science">
      <p style="color:var(--txt-2);font-size:14px;line-height:1.8;margin:16px 0">
        从天眼探宇到散裂探物质，从同步辐射到宇宙线观测——中国大科学装置已跻身世界前列，在天文、材料、生命科学等多个前沿领域提供了世界级实验平台。
      </p>

      <div class="company" id="proj-fast">
        <h3>FAST 天眼 — 500米口径球面射电望远镜 <span class="tl-badge badge-cn">正常运行</span></h3>
        <div class="en">贵州省平塘县 · 世界最大单口径射电望远镜 · 2016年落成</div>
        <p>中国天文领域的标志性大科学装置，口径达500米，接收面积相当于30个足球场。自开放运营以来，已发现超过900颗新脉冲星。开放竞争制度，每年向全球天文学家公开申请观测时间，是世界天文研究的重要公共平台。</p>
        <div class="company-grid">
          <div class="kv"><div class="k">口径</div><div class="v">500m（世界第一）</div></div>
          <div class="kv"><div class="k">发现脉冲星</div><div class="v">900+ 颗</div></div>
          <div class="kv"><div class="k">接收面积</div><div class="v">30个足球场</div></div>
          <div class="kv"><div class="k">运营模式</div><div class="v">全球开放竞争</div></div>
        </div>
      </div>

      <div class="company" id="proj-csns">
        <h3>中国散裂中子源 (CSNS) — 探物质微观结构的先进平台 <span class="tl-badge badge-cn">运行</span></h3>
        <div class="en">广东东莞 · 世界第四座装置 · 2018年通过验收</div>
        <p>中国首座数据类大科学装置，为材料科学、生命科学、化学、纯物理等领域提供先进的中子散裂实验手段。加速器主要参数达国际先进水平，年运行超过5000小时，对外开放试验课题超过500项。</p>
        <div class="company-grid">
          <div class="kv"><div class="k">装置类型</div><div class="v">中子散裂源</div></div>
          <div class="kv"><div class="k">年运行</div><div class="v">5000+ 小时</div></div>
          <div class="kv"><div class="k">对外课题</div><div class="v">500+ 项</div></div>
          <div class="kv"><div class="k">升级计划</div><div class="v">CSNS-II 已启动，束流壁陡倍增</div></div>
        </div>
      </div>

      <div class="company" id="proj-ssrf">
        <h3>上海同步辐射光源 (SSRF) <span class="tl-badge badge-cn">运行</span></h3>
        <div class="en">上海张江 · 第三代同步辐射光源 · 每年服务超过3万科研人次</div>
        <p>中国最大的同步辐射光源装置，为微固物理、结构生物学、化学识别、材料科学等领域提供高亮度 X 射线。具有多条干线站和座特立实验站点，是亚洲最强同步辐射装置之一。</p>
        <div class="company-grid">
          <div class="kv"><div class="k">能量</div><div class="v">3.5 GeV</div></div>
          <div class="kv"><div class="k">干线站</div><div class="v">40+ 条</div></div>
          <div class="kv"><div class="k">服务次数</div><div class="v">3万+人次/年</div></div>
          <div class="kv"><div class="k">升级</div><div class="v">SSRF-II 立项研究</div></div>
        </div>
      </div>

      <div class="company" id="proj-lhaaso">
        <h3>高海拔宇宙线观测站 (LHAASO) <span class="tl-badge badge-cn">运行</span></h3>
        <div class="en">四川稻城 · 4410m 海拔 · 2021年全线运行</div>
        <p>世界最高效率的宇宙线观测站，位于川西稻城4410米高海拔地区。致力于探索高能宇宙线起源、宇宙线加速机制、暗物质等前沿科学问题。已探测到多个 PeV 级别的宇宙线加速源，打破了传统理论界限。</p>
        <div class="company-grid">
          <div class="kv"><div class="k">海拔</div><div class="v">4410m</div></div>
          <div class="kv"><div class="k">检测范围</div><div class="v">&#947;天文 + 宇宙线</div></div>
          <div class="kv"><div class="k">重要发现</div><div class="v">PeV级加速源</div></div>
          <div class="kv"><div class="k">国际地位</div><div class="v">世界领先</div></div>
        </div>
      </div>

      <div class="company" id="proj-heps">
        <h3>高能同步辐射光源 (HEPS) <span class="tl-badge badge-private">建设中</span></h3>
        <div class="en">北京怀柔 · 第四代同步辐射光源 · 世界最低发散度</div>
        <p>中国正在建设的第四代同步辐射光源，也是世界上发散度最低的同步辐射装置。主体结构已封顶，加速器按计划进行安装。将为材料科学、能源环境、生命科学等提供先进的 X 射线实验手段。</p>
        <div class="company-grid">
          <div class="kv"><div class="k">装置类型</div><div class="v">第四代同步辐射</div></div>
          <div class="kv"><div class="k">能量</div><div class="v">6 GeV</div></div>
          <div class="kv"><div class="k">建设进度</div><div class="v">主体封顶，加速器安装</div></div>
          <div class="kv"><div class="k">计划投运</div><div class="v">2027年前后</div></div>
        </div>
      </div>
    </div>
"""

c = c.replace(
    '<!-- ===== 公共时间线（始终可见） ===== -->',
    panel + '\n    <!-- ===== 公共时间线（始终可见） ===== -->'
)

# 3. Timeline entries
tl = """        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128300;</span><span class="pt-name pt-link" data-target="proj-fast" data-tab="tab-science">FAST 天眼</span><span class="pt-status st-ready">运行</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2016</span><span class="pt-badge bg-start">落成</span><span class="pt-title">FAST 落成，全球最大单口径射电望远镜</span></div>
          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">截至现在</span><span class="pt-badge bg-prog">发现</span><span class="pt-title">已发现900+颗脉冲星</span></div>
        </div></div>
        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128300;</span><span class="pt-name pt-link" data-target="proj-csns" data-tab="tab-science">散裂中子源</span><span class="pt-status st-ready">运行</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2018</span><span class="pt-badge bg-start">验收</span><span class="pt-title">中国首座数据类大科学装置通过国家验收</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">未来</span><span class="pt-badge bg-plan">升级</span><span class="pt-title">CSNS-II 已启动，束流壁陡倍增</span></div>
        </div></div>
        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128300;</span><span class="pt-name pt-link" data-target="proj-heps" data-tab="tab-science">HEPS</span><span class="pt-status st-building">建设中</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">截至730</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">主体封顶，加速器安装</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2027</span><span class="pt-badge bg-plan">投运</span><span class="pt-title">计划2027年前后投运</span></div>
        </div></div>"""

c = c.replace(
    'data-tab="tab-energy">浙江特高压环网',
    tl + '\n            data-tab="tab-energy">浙江特高压环网'
)

with open(r"D:\13191\Documents\workbuddyspace\2026-07-26-13-55-46\rocket-news\mega-projects.html","w",encoding="utf-8") as f:
    f.write(c)

print("Done!")
