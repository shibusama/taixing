import re

path = r"D:\13191\Documents\workbuddyspace\2026-07-26-13-55-46\rocket-news\mega-projects.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Find the broken area: the pt-group for 浙江特高压环网 got split
# We need to fix it and properly insert the new timeline entries

# Find the last energy pt-group (陇电入浙) ending
last_energy_end = c.rfind('        </div></div>\n\n            <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#9889;</span>')

if last_energy_end > 0:
    # Find where this pt-group ends
    rest = c[last_energy_end:]
    end_match = re.search(r'        </div></div>', rest)
    if end_match:
        end_pos = last_energy_end + end_match.end()
        # Now find where the science entries start (the ones we wrongly inserted)
        sci_start = c.find('        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128300;</span>', end_pos)
        
        if sci_start > 0:
            # Find where the science entries end
            sci_rest = c[sci_start:]
            sci_end_match = re.search(r'        </div></div>', sci_rest)
            if sci_end_match:
                # Find third closing (three science groups)
                third_close = sci_rest.find('        </div></div>', sci_end_match.end())
                if third_close > 0:
                    sci_end_pos = sci_start + third_close + len('        </div></div>')
                else:
                    sci_end_pos = sci_start + sci_end_match.end()
                
                # Extract the science entries
                science_entries = c[sci_start:sci_end_pos]
                
                # Remove everything from end_pos to the next proper structure
                # Find where the proper 浙江特高压环网 pt-group starts
                zj_start = c.find('data-tab="tab-energy">浙江特高压环网</span>', sci_end_pos)
                if zj_start > 0:
                    # Find the beginning of this pt-group
                    zj_group_start = c.rfind('<div class="pt-group"', 0, zj_start)
                    if zj_group_start > 0:
                        # Remove the broken section
                        broken = c[end_pos:zj_group_start]
                        c = c[:end_pos] + c[zj_group_start:]
                        
                        # Now insert science entries right after the last energy group
                        # Re-find the end of 陇电入浙 after removal
                        last_energy = c.rfind('        </div></div>\n\n            <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#9889;</span>')
                        rest2 = c[last_energy:]
                        end2 = re.search(r'        </div></div>', rest2)
                        if end2:
                            insert_pos = last_energy + end2.end()
                            c = c[:insert_pos] + '\n' + science_entries + c[insert_pos:]

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Done! Timeline fixed.")
path = r"D:\13191\Documents\workbuddyspace\2026-07-26-13-55-46\rocket-news\mega-projects.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

target = '<div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#9889;</span><span class="pt-name pt-link" data-target="proj-zhejiang-ring" data-tab="tab-energy">浙江特高压环网</span><span class="pt-status st-building">在建</span></div><div class="pt-items">'
new_pt = '<div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#9889;</span><span class="pt-name pt-link" data-target="proj-zhejiang-ring" data-tab="tab-energy">浙江特高压环网</span><span class="pt-status st-building">在建</span></div><div class="pt-items">'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2026.4</span><span class="pt-badge bg-start">开工</span><span class="pt-title">七地同步开工，293亿</span></div>'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">2026.6</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">宁绍站开工，首座千kV变电站</span></div>'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2029</span><span class="pt-badge bg-plan">投运</span><span class="pt-title">计划2029年投运</span></div>'
new_pt += '\n        </div></div>'

new_pt += '\n\n        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128300;</span><span class="pt-name pt-link" data-target="proj-fast" data-tab="tab-science">FAST 天眼</span><span class="pt-status st-ready">运行</span></div><div class="pt-items">'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2016</span><span class="pt-badge bg-start">落成</span><span class="pt-title">FAST 落成，全球最大单口径射电望远镜</span></div>'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">截至现在</span><span class="pt-badge bg-prog">发现</span><span class="pt-title">已发现900+颗脉冲星</span></div>'
new_pt += '\n        </div></div>'

new_pt += '\n\n        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128300;</span><span class="pt-name pt-link" data-target="proj-csns" data-tab="tab-science">散裂中子源</span><span class="pt-status st-ready">运行</span></div><div class="pt-items">'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-green"></div><span class="pt-date">2018</span><span class="pt-badge bg-start">验收</span><span class="pt-title">中国首座数据类大科学装置通过国家验收</span></div>'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">未来</span><span class="pt-badge bg-plan">升级</span><span class="pt-title">CSNS-II 已启动，束流壁陡倍增</span></div>'
new_pt += '\n        </div></div>'

new_pt += '\n\n        <div class="pt-group"><div class="pt-header"><span class="pt-emoji">&#128300;</span><span class="pt-name pt-link" data-target="proj-heps" data-tab="tab-science">HEPS</span><span class="pt-status st-building">建设中</span></div><div class="pt-items">'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-cyan"></div><span class="pt-date">截至730</span><span class="pt-badge bg-prog">进度</span><span class="pt-title">主体封顶，加速器安装</span></div>'
new_pt += '\n          <div class="pt-item"><div class="pt-marker mk-gold"></div><span class="pt-date">2027</span><span class="pt-badge bg-plan">投运</span><span class="pt-title">计划2027年前后投运</span></div>'
new_pt += '\n        </div></div>'

old_pos = c.find('data-target="proj-zhejiang-ring" data-tab="tab-energy">浙江特高压环网</span>')
if old_pos > 0:
    # Find the start of this pt-group
    start = c.rfind('<div class="pt-group"', 0, old_pos)
    # Find end of this pt-group (next </div></div>)
    end = c.find('</div></div>', old_pos)
    end = c.find('</div></div>', end + 12)  # skip first </div></div> (items closing)
    if end > 0:
        end += len('</div></div>')
        # Also remove the broken science entries that were wrongly inserted
        # Find where the next proper pt-group starts
        next_group = c.find('<div class="pt-group"', end)
        if next_group > 0:
            c = c[:start] + new_pt + '\n' + c[next_group:]
        else:
            c = c[:start] + new_pt + '\n      </div>' + c[end:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print("Fixed!")
    else:
        print("Could not find end of pt-group")
else:
    print("Could not find target")
