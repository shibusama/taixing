import re

with open(r"D:\13191\Documents\workbuddyspace\2026-07-26-13-55-46\rocket-news\mega-projects.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Tab button
content = content.replace(
    '<button data-tab="tab-energy">\u26a1 \u80fd\u6e90\u52a8\u8109</button>',
    '<button data-tab="tab-energy">\u26a1 \u80fd\u6e90\u52a8\u8109</button>\n      <button data-tab="tab-science">\U0001f52c \u5927\u79d1\u5b66\u88c5\u7f6e</button>'
)

# 2. Science tab panel  
panel = (
    '    <!-- ===== Tab 4: \u5927\u79d1\u5b66\u88c5\u7f6e ===== -->\n'
    '    <div class="tab-panel" id="tab-science">\n'
    '      <p style="color:var(--txt-2);font-size:14px;line-height:1.8;margin:16px 0">\n'
    '        \u4ece\u5929\u773c\u63a2\u5b87\u5230\u6563\u88c2\u63a2\u7269\u8d28\uff0c\u4ece\u540c\u6b65\u8f90\u5c04\u5230\u5b87\u5b99\u7ebf\u89c2\u6d4b\u2014\u2014\u4e2d\u56fd\u5927\u79d1\u5b66\u88c5\u7f6e\u5df2\u8dfb\u8eab\u4e16\u754c\u524d\u5217\uff0c\u5728\u5929\u6587\u3001\u6750\u6599\u3001\u751f\u547d\u79d1\u5b66\u7b49\u591a\u4e2a\u524d\u6cbf\u9886\u57df\u63d0\u4f9b\u4e86\u4e16\u754c\u7ea7\u5b9e\u9a8c\u5e73\u53f0\u3002\n'
    '      </p>\n\n'
    '      <div class="company" id="proj-fast">\n'
    '        <h3>FAST \u5929\u773c \u2014 500\u7c73\u53e3\u5f84\u7403\u9762\u5c04\u7535\u671b\u8fdc\u955c <span class="tl-badge badge-cn">\u6b63\u5e38\u8fd0\u884c</span></h3>\n'
    '        <div class="en">\u8d35\u5dde\u7701\u5e73\u5858\u53bf \u00b7 \u4e16\u754c\u6700\u5927\u5355\u53e3\u5f84\u5c04\u7535\u671b\u8fdc\u955c \u00b7 2016\u5e74\u843d\u6210</div>\n'
    '        <p>\u4e2d\u56fd\u5929\u6587\u9886\u57df\u7684\u6807\u5fd7\u6027\u5927\u79d1\u5b66\u88c5\u7f6e\uff0c\u53e3\u5f84\u8fbe500\u7c73\uff0c\u63a5\u6536\u9762\u79ef\u76f8\u5f53\u4e8e30\u4e2a\u8db3\u7403\u573a\u3002\u81ea\u5f00\u653e\u8fd0\u8425\u4ee5\u6765\uff0c\u5df2\u53d1\u73b0\u8d85\u8fc7900\u9897\u65b0\u8109\u51b2\u661f\u3002\u5f00\u653e\u7ade\u4e89\u5236\uff0c\u5e74\u5411\u5168\u7403\u5929\u6587\u5b66\u5bb6\u516c\u5f00\u7533\u8bf7\u89c2\u6d4b\u65f6\u95f4\uff0c\u662f\u4e16\u754c\u5929\u6587\u7814\u7a76\u7684\u91cd\u8981\u516c\u5171\u5e73\u53f0\u3002</p>\n'
    '        <div class="company-grid">\n'
    '          <div class="kv"><div class="k">\u53e3\u5f84</div><div class="v">500m\uff08\u4e16\u754c\u7b2c\u4e00\uff09</div></div>\n'
    '          <div class="kv"><div class="k">\u53d1\u73b0\u8109\u51b2\u661f</div><div class="v">900+ \u9897</div></div>\n'
    '          <div class="kv"><div class="k">\u63a5\u6536\u9762\u79ef</div><div class="v">30\u4e2a\u8db3\u7403\u573a</div></div>\n'
    '          <div class="kv"><div class="k">\u8fd0\u8425\u6a21\u5f0f</div><div class="v">\u5168\u7403\u5f00\u653e\u7ade\u4e89</div></div>\n'
    '        </div>\n'
    '      </div>\n\n'
    '      <div class="company" id="proj-csns">\n'
    '        <h3>\u4e2d\u56fd\u6563\u88c2\u4e2d\u5b50\u6e90 (CSNS) \u2014 \u63a2\u7269\u8d28\u5fae\u89c2\u7ed3\u6784\u7684\u5148\u8fdb\u5e73\u53f0 <span class="tl-badge badge-cn">\u8fd0\u884c</span></h3>\n'
    '        <div class="en">\u5e7f\u4e1c\u4e1c\u839e \u00b7 \u4e16\u754c\u7b2c\u56db\u5ea7\u88c5\u7f6e \u00b7 2018\u5e74\u901a\u8fc7\u9a8c\u6536</div>\n'
    '        <p>\u4e2d\u56fd\u9996\u5ea7\u6570\u636e\u7c7b\u5927\u79d1\u5b66\u88c5\u7f6e\uff0c\u4e3a\u6750\u6599\u79d1\u5b66\u3001\u751f\u547d\u79d1\u5b66\u3001\u5316\u5b66\u3001\u7eaf\u7269\u7406\u7b49\u9886\u57df\u63d0\u4f9b\u5148\u8fdb\u7684\u4e2d\u5b50\u6563\u88c2\u5b9e\u9a8c\u624b\u6bb5\u3002\u52a0\u901f\u5668\u4e3b\u8981\u53c2\u6570\u8fbe\u56fd\u9645\u5148\u8fdb\u6c34\u5e73\uff0c\u5e74\u8fd0\u884c\u8d85\u8fc75000\u5c0f\u65f6\uff0c\u5bf9\u5916\u5f00\u653e\u8bd5\u9a8c\u8bfe\u9898\u8d85\u8fc7500\u9879\u3002</p>\n'
    '        <div class="company-grid">\n'
    '          <div class="kv"><div class="k">\u88c5\u7f6e\u7c7b\u578b</div><div class="v">\u4e2d\u5b50\u6563\u88c2\u6e90</div></div>\n'
    '          <div class="kv"><div class="k">\u5e74\u8fd0\u884c</div><div class="v">5000+ \u5c0f\u65f6</div></div>\n'
    '          <div class="kv"><div class="k">\u5bf9\u5916\u8bfe\u9898</div><div class="v">500+ \u9879</div></div>\n'
    '          <div class="kv"><div class="k">\u5347\u7ea7\u8ba1\u5212</div><div class="v">CSNS-II \u5df2\u542f\u52a8\uff0c\u8c61\u6d41\u58c1\u5d1b\u500d\u589e</div></div>\n'
    '        </div>\n'
    '      </div>\n\n'
    '      <div class="company" id="proj-ssrf">\n'
    '        <h3>\u4e0a\u6d77\u540c\u6b65\u8f90\u5c04\u5149\u6e90 (SSRF) <span class="tl-badge badge-cn">\u8fd0\u884c</span></h3>\n'
    '        <div class="en">\u4e0a\u6d77\u5f20\u6c5f \u00b7 \u7b2c\u4e09\u4ee3\u540c\u6b65\u8f90\u5c04\u5149\u6e90 \u00b7 \u6bcf\u5e74\u670d\u52a1\u8d85\u8fc73\u4e07\u79d1\u7814\u4eba\u6b21</div>\n'
    '        <p>\u4e2d\u56fd\u6700\u5927\u7684\u540c\u6b65\u8f90\u5c04\u5149\u6e90\u88c5\u7f6e\uff0c\u4e3a\u5fae\u56fa\u7269\u7406\u3001\u7ed3\u6784\u751f\u7269\u5b66\u3001\u5316\u5b66\u8bc6\u522b\u3001\u6750\u6599\u79d1\u5b66\u7b49\u9886\u57df\u63d0\u4f9b\u9ad8\u4eae\u5ea6 X \u5c04\u7ebf\u3002\u5177\u6709\u591a\u6761\u5e72\u7ebf\u7ad9\u548c\u5ea7\u7279\u7acb\u5b9e\u9a8c\u7ad9\u70b9\uff0c\u662f\u4e9a\u6d32\u6700\u5f3a\u540c\u6b65\u8f90\u5c04\u88c5\u7f6e\u4e4b\u4e00\u3002</p>\n'
    '        <div class="company-grid">\n'
    '          <div class="kv"><div class="k">\u80fd\u91cf</div><div class="v">3.5 GeV</div></div>\n'
    '          <div class="kv"><div class="k">\u5e72\u7ebf\u7ad9</div><div class="v">40+ \u6761</div></div>\n'
    '          <div class="kv"><div class="k">\u670d\u52a1\u6b21\u6570</div><div class="v">3\u4e07+\u4eba\u6b21/\u5e74</div></div>\n'
    '          <div class="kv"><div class="k">\u5347\u7ea7</div><div class="v">SSRF-II \u7acb\u9879\u7814\u7a76</div></div>\n'
    '        </div>\n'
    '      </div>\n\n'
    '      <div class="company" id="proj-lhaaso">\n'
    '        <h3>\u9ad8\u6d77\u62d4\u5b87\u5b99\u7ebf\u89c2\u6d4b\u7ad9 (LHAASO) <span class="tl-badge badge-cn">\u8fd0\u884c</span></h3>\n'
    '        <div class="en">\u56db\u5ddd\u7a3b\u57ce \u00b7 4410m \u6d77\u62d4 \u00b7 2021\u5e74\u5168\u7ebf\u8fd0\u884c</div>\n'
    '        <p>\u4e16\u754c\u6700\u9ad8\u6548\u7387\u7684\u5b87\u5b99\u7ebf\u89c2\u6d4b\u7ad9\uff0c\u4f4d\u4e8e\u5ddd\u897f\u7a3b\u57ce4410\u7c73\u9ad8\u6d77\u62d4\u5730\u533a\u3002\u81f4\u529b\u4e8e\u63a2\u7d22\u9ad8\u80fd\u5b87\u5b99\u7ebf\u8d77\u6e90\u3001\u5b87\u5b99\u7ebf\u52a0\u901f\u673a\u5236\u3001\u6635\u70ed\u9ed1\u7269\u8d28\u7b49\u524d\u6cbf\u79d1\u5b66\u95ee\u9898\u3002\u5df2\u68c0\u6d4b\u5230\u591a\u4e2a PeV \u7ea7\u522b\u7684\u5b87\u5b99\u7ebf\u52a0\u901f\u6e90\uff0c\u6253\u7834\u4e86\u4f20\u7edf\u7406\u8bba\u754c\u9650\u3002</p>\n'
    '        <div class="company-grid">\n'
    '          <div class="kv"><div class="k">\u6d77\u62d4</div><div class="v">4410m</div></div>\n'
    '          <div class="kv"><div class="k">\u68c0\u6d4b\u8303\u56f4</div><div class="v">\u03b3\u5929\u6587 + \u5b87\u5b99\u7ebf</div></div>\n'
    '          <div class="kv"><div class="k">\u91cd\u8981\u53d1\u73b0</div><div class="v">PeV\u7ea7\u52a0\u901f\u6e90</div></div>\n'
    '          <div class="kv"><div class="k">\u56fd\u9645\u5730\u4f4d</div><div class="v">\u4e16\u754c\u9886\u5148</div></div>\n'
    '        </div>\n'
    '      </div>\n\n'
    '      <div class="company" id="proj-heps">\n'
    '        <h3>\u9ad8\u80fd\u540c\u6b65\u8f90\u5c04\u5149\u6e90 (HEPS) <span class="tl-badge badge-private">\u5efa\u8bbe\u4e2d</span></h3>\n'
    '        <div class="en">\u5317\u4eac\u6000\u67d4 \u00b7 \u7b2c\u56db\u4ee3\u540c\u6b65\u8f90\u5c04\u5149\u6e90 \u00b7 \u4e16\u754c\u6700\u4f4e\u53d1\u6563\u5ea6</div>\n'
    '        <p>\u4e2d\u56fd\u6b63\u5728\u5efa\u8bbe\u7684\u7b2c\u56db\u4ee3\u540c\u6b65\u8f90\u5c04\u5149\u6e90\uff0c\u4e5f\u662f\u4e16\u754c\u4e0a\u53d1\u6563\u5ea6\u6700\u4f4e\u7684\u540c\u6b65\u8f90\u5c04\u88c5\u7f6e\u3002\u4e3b\u4f53\u7ed3\u6784\u5df2\u5c01\u9876\uff0c\u52a0\u901f\u5668\u6309\u8ba1\u5212\u8fdb\u884c\u5b89\u88c5\u3002\u5c06\u4e3a\u6750\u6599\u79d1\u5b66\u3001\u80fd\u6e90\u73af\u5883\u3001\u751f\u547d\u79d1\u5b66\u7b49\u63d0\u4f9b\u5148\u8fdb\u7684 X \u5c04\u7ebf\u5b9e\u9a8c\u624b\u6bb5\u3002</p>\n'
    '        <div class="company-grid">\n'
    '          <div class="kv"><div class="k">\u88c5\u7f6e\u7c7b\u578b</div><div class="v">\u7b2c\u56db\u4ee3\u540c\u6b65\u8f90\u5c04</div></div>\n'
    '          <div class="kv"><div class="k">\u80fd\u91cf</div><div class="v">6 GeV</div></div>\n'
    '          <div class="kv"><div class="k">\u5efa\u8bbe\u8fdb\u5ea6</div><div class="v">\u4e3b\u4f53\u5c01\u9876\uff0c\u52a0\u901f\u5668\u5b89\u88c5</div></div>\n'
    '          <div class="kv"><div class="k">\u8ba1\u5212\u6295\u8fd0</div><div class="v">2027\u5e74\u524d\u540e</div></div>\n'
    '        </div>\n'
    '      </div>\n'
    '    </div>\n'
)

content = content.replace(
    '    <!-- ===== \u516c\u5171\u65f6\u95f4\u7ebf\uff08\u59cb\u7ec8\u53ef\u89c1\uff09===== -->',
    panel + '\n\n    <!-- ===== \u516c\u5171\u65f6\u95f4\u7ebf\uff08\u59cb\u7ec8\u53ef\u89c1\uff09===== -->'
)

# 3. Timeline entries
timeline = (
    '        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">\U0001f52c</span><span class="pt-name pt-link" data-target="proj-fast" data-tab="tab-science">FAST \u5929\u773c</span><span class="pt-status st-ready">\u8fd0\u884c</span></div><div class="pt-items">\n'
    '          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2016</span><span class="pt-badge bg-start">\u843d\u6210</span><span class="pt-title">FAST \u843d\u6210\uff0c\u5168\u7403\u6700\u5927\u5355\u53e3\u5f84\u5c04\u7535\u671b\u8fdc\u955c</span></div>\n'
    '          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">\u622a\u81f3\u73b0\u5728</span><span class="pt-badge bg-prog">\u53d1\u73b0</span><span class="pt-title">\u5df2\u53d1\u73b0900+\u9897\u8109\u51b2\u661f</span></div>\n'
    '        </div></div>\n'
    '        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">\U0001f52c</span><span class="pt-name pt-link" data-target="proj-csns" data-tab="tab-science">\u6563\u88c2\u4e2d\u5b50\u6e90</span><span class="pt-status st-ready">\u8fd0\u884c</span></div><div class="pt-items">\n'
    '          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2018</span><span class="pt-badge bg-start">\u9a8c\u6536</span><span class="pt-title">\u4e2d\u56fd\u9996\u5ea7\u6570\u636e\u7c7b\u5927\u79d1\u5b66\u88c5\u7f6e\u901a\u8fc7\u56fd\u5bb6\u9a8c\u6536</span></div>\n'
    '          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">\u672a\u6765</span><span class="pt-badge bg-plan">\u5347\u7ea7</span><span class="pt-title">CSNS-II \u5df2\u542f\u52a8\uff0c\u8c61\u6d41\u58c1\u5d1b\u500d\u589e</span></div>\n'
    '        </div></div>\n'
    '        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">\U0001f52c</span><span class="pt-name pt-link" data-target="proj-heps" data-tab="tab-science">HEPS</span><span class="pt-status st-building">\u5efa\u8bbe\u4e2d</span></div><div class="pt-items">\n'
    '          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">\u622a\u81f3730</span><span class="pt-badge bg-prog">\u8fdb\u5ea6</span><span class="pt-title">\u4e3b\u4f53\u5c01\u9876\uff0c\u52a0\u901f\u5668\u5b89\u88c5</span></div>\n'
    '          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2027</span><span class="pt-badge bg-plan">\u6295\u8fd0</span><span class="pt-title">\u8ba1\u52122027\u5e74\u524d\u540e\u6295\u8fd0</span></div>\n'
    '        </div></div>'
)

content = content.replace(
    '            <div class="pt-group"><div class="pt-header"><span class="pt-emoji">\u26a1</span><span class="pt-name pt-link" data-target="proj-zhejiang-ring" data-tab="tab-energy">\u6d59\u6c5f\u7279\u9ad8\u538b\u73af\u7f51</span>',
    timeline + '\n            <div class="pt-group"><div class="pt-header"><span class="pt-emoji">\u26a1</span><span class="pt-name pt-link" data-target="proj-zhejiang-ring" data-tab="tab-energy">\u6d59\u6c5f\u7279\u9ad8\u538b\u73af\u7f51</span>'
)

with open(r"D:\13191\Documents\workbuddyspace\2026-07-26-13-55-46\rocket-news\mega-projects.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Done!")
