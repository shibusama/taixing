import re, os

path = r"D:\13191\Documents\workbuddyspace\2026-07-26-13-55-46\rocket-news\mega-projects.html"
backup = path + ".bak"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

os.makedirs(os.path.dirname(backup), exist_ok=True)
with open(backup, "w", encoding="utf-8") as f:
    f.write(c)

# Find pt-groups section
start = c.find('<div class="pt-groups">')
if start < 0:
    print("ERROR: pt-groups not found!")
    exit(1)

# Find closing of pt-groups
i = start + len('<div class="pt-groups">')
depth = 0
while i < len(c):
    if c[i:i+5] in ['<div ', '<div>'] or (c[i:i+4] == '<div' and c[i+4] in ' >'):
        depth += 1
        i += 1
    elif c[i:i+6] == '</div>':
        depth -= 1
        i += 6
        if depth == 0:
            break
    else:
        i += 1

end = i
old_section = c[start:end]
print(f"Old section length: {len(old_section)}")

# Build the correct pt-groups section
new_section = '''    <div class="pt-groups">

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128646;</span><span class="pt-name pt-link" data-target="proj-sichuan-tibet" data-tab="tab-transport">川藏铁路雅林段</span><span class="pt-status st-building">在建</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">截至7月</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">隧道78.3%，三座控制隧道全贯通</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2027.9</span><span class="pt-badge bg-plan">计划</span><span class="pt-title">雅康段通车</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2030</span><span class="pt-badge bg-plan">计划</span><span class="pt-title">全线贯通，2031通车</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128642;</span><span class="pt-name pt-link" data-target="proj-china-kyrgyz-uzbek" data-tab="tab-transport">中吉乌铁路</span><span class="pt-status st-building">在建</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2024.12</span><span class="pt-badge bg-start">开工</span><span class="pt-title">吉国段启动</span></div>
          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2026.2</span><span class="pt-badge bg-start">开工</span><span class="pt-title">全线实体攻坚，18座隧道掘进</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2030</span><span class="pt-badge bg-plan">计划</span><span class="pt-title">通车，可能提前至2028-29</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128674;</span><span class="pt-name pt-link" data-target="proj-zhanhai" data-tab="tab-transport">湛海高铁</span><span class="pt-status st-ready">即将开工</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2025.12</span><span class="pt-badge bg-approve">批复</span><span class="pt-title">发改委批可研，402亿，工期4年</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#127754;</span><span class="pt-name pt-link" data-target="proj-bohai" data-tab="tab-transport">渤海海峡通道</span><span class="pt-status st-plan">规划中</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">论证中</span><span class="pt-badge bg-plan">论证</span><span class="pt-title">123km海底隧道，已入国家规划</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#9973;</span><span class="pt-name pt-link" data-target="proj-three-gorges" data-tab="tab-water">三峡水运新通道</span><span class="pt-status st-building">在建</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2026.6.8</span><span class="pt-badge bg-start">开工</span><span class="pt-title">"十五五"首个标志性工程破土</span></div>
          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">2026.10</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">850万m&#179;先行开挖区完成</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2035前后</span><span class="pt-badge bg-plan">计划</span><span class="pt-title">建成通航，年通过3.36亿吨</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128674;</span><span class="pt-name pt-link" data-target="proj-pinglu" data-tab="tab-water">平陆运河</span><span class="pt-status st-ready">即将通航</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">截至6月</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">投资完成97%，全面有水调试</span></div>
          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2026.9</span><span class="pt-badge bg-start">通航</span><span class="pt-title">正式通航，5000吨级直达北部湾</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128167;</span><span class="pt-name pt-link" data-target="proj-yinjiang" data-tab="tab-water">引江补汉</span><span class="pt-status st-building">在建</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">截至6月</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">主隧洞&gt;29km，支洞&gt;42km，9台TBM</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">持续推进</span><span class="pt-badge bg-plan">计划</span><span class="pt-title">出口段已提前4个月贯通</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128167;</span><span class="pt-name pt-link" data-target="proj-snd-west" data-tab="tab-water">南水北调西线</span><span class="pt-status st-plan">规划中</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">十五五</span><span class="pt-badge bg-plan">计划</span><span class="pt-title">力争开工，年调水170亿m&#179;</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#9889;</span><span class="pt-name pt-link" data-target="proj-longdian" data-tab="tab-energy">陇电入浙</span><span class="pt-status st-building">在建</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">截至6月</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">浙江段贯通，越州站投运，联调完成</span></div>
          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2026底</span><span class="pt-badge bg-start">带电</span><span class="pt-title">具备带电调试条件</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2027</span><span class="pt-badge bg-plan">投运</span><span class="pt-title">正式投运，年送电360亿kWh</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#9889;</span><span class="pt-name pt-link" data-target="proj-zhejiang-ring" data-tab="tab-energy">浙江特高压环网</span><span class="pt-status st-building">在建</span></div><div class="pt-items">
          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2026.4</span><span class="pt-badge bg-start">开工</span><span class="pt-title">七地同步开工，293亿</span></div>
          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">2026.6</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">宁绍站开工，首座千kV变电站</span></div>
          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2029</span><span class="pt-badge bg-plan">投运</span><span class="pt-title">计划2029年投运</span></div>
        </div></div>

        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128300;</span><span class="pt-name pt-link" data-target="proj-fast" data-tab="tab-science">FAST 天眼</span><span class="pt-status st-ready">运行</span></div><div class="pt-items">
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
        </div></div>

      </div>'''

c = c[:start] + new_section + c[end:]

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Done! Timeline fully rebuilt with 13 entries.")
