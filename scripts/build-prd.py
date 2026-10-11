"""Build the review boards and illustrated PRD. Requires Pillow and reportlab.

Run from any directory after render-prototype.mjs. Use CHEKI_CJK_FONT to select
a TrueType font with Chinese glyphs on systems without macOS Arial Unicode.
"""
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / 'docs/prototype'
SCREENS = PROTOTYPE / 'screens'
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
FONT = os.environ.get('CHEKI_CJK_FONT', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
pdfmetrics.registerFont(TTFont('CJK', FONT))
INK, MUTED, ROSE, PAPER, LINE = '#292724', '#81796e', '#b84b64', '#faf8f4', '#e4ddd3'
PAGE_W, PAGE_H = 841.89, 595.28
SOURCE = (ROOT / 'docs/PRD.md').read_text()

SCENES = [
    ('home', '日期首页', '日期是主线，活动不是门槛', 'AC01 / AC02 / AC09', '样例：3 个日期、常规 17 张、特殊 1 张、已记录总花费 1100 元。'),
    ('quick', '快速记录', '选好日期，就能记一笔', 'AC02 / AC03 / AC13 / AC15 / AC16', '活动选填默认收起；空活动不需要确认，也不产生待补提醒。'),
    ('batch', '按日补录', '一次整理这一天的多笔记录', 'AC01 / AC09 / AC12', '本次新增与当天已有合计分开；不填活动直接保存为空。'),
    ('day', '当日记录', '同一天的拍立得，一起回顾', 'AC05 / AC07 / AC08 / AC09', '样例 10 月 11 日：常规 7 张、特殊 1 张、已记录 450 元；均可无活动。'),
    ('idol', '偶像', '沿着日期，回顾每次见面', 'AC01 / AC07 / AC09', '样例小凪：8 张、580 元、3 个记录日。记录日不等于活动场次。'),
    ('stats', '统计', '按日期看清数量与花费', 'AC01 / AC02 / AC07 / AC09', '统计读取每笔日期，不依赖活动；自选日期和类型金额明细待补。'),
    ('album', '相册', '记录有日期，照片就有归处', 'AC06 / AC07 / AC08', '当前图像为虚构示例插画；没有活动也能保存和浏览照片。'),
    ('data', '数据管理', '日期、可选活动与照片，完整带走', 'AC10 / AC11', 'CSV 可实际下载；ZIP 与恢复仅模拟流程，正式功能待实现。'),
]

def font(size):
    return ImageFont.truetype(FONT, size)

def make_board(items, name, title, subtitle, start):
    board = Image.new('RGB', (1920, 1230), '#efece6')
    d = ImageDraw.Draw(board)
    d.text((70, 35), 'CHEKI DIARY  /  PRODUCT PROTOTYPE  /  2026.10.11', font=font(16), fill=ROSE)
    d.text((70, 72), title, font=font(44), fill=INK)
    d.text((70, 136), subtitle, font=font(20), fill=MUTED)
    for idx, (key, label, *_) in enumerate(items):
        x, y = 80 + idx * 445, 242
        d.text((x + 3, 203), f'{idx+start:02d}  {label}', font=font(22), fill=INK)
        image = Image.open(SCREENS / f'{key}.png').convert('RGB').resize((390, 844), Image.Resampling.LANCZOS)
        mask = Image.new('L', image.size)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 389, 843), radius=28, fill=255)
        d.rounded_rectangle((x-3, y-3, x+393, y+847), radius=31, fill='#d9d1c7')
        board.paste(image, (x, y), mask)
    d.line((70, 1133, 1845, 1133), fill='#d8d0c7', width=1)
    d.text((70, 1161), '原型评审稿 v0.4  ·  虚构演示数据  ·  平台待定', font=font(17), fill=MUTED)
    d.text((1490, 1161), '日期为主  ·  活动选填', font=font(17), fill=ROSE)
    board.save(PROTOTYPE / name)

make_board(SCENES[:4], 'recording-overview.png', '推活日记  /  按日期记录每次见面', '日期必填，活动选填。直接记住和谁拍了多少张、花了多少钱。', 1)
make_board(SCENES[4:], 'review-overview.png', '推活日记  /  回顾与保存', '从日期时间线到私人相册，常规切数与特殊收藏分开回顾。', 5)
make_board([('quick-group','团切录入'),('quick-special','特殊 cheki 录入'),('group','团体记录'),('special','特殊收藏')], 'special-overview.png', '推活日记  /  团体与特殊 cheki', '团切归属一个团体；特殊可关联多位偶像，数量不计入常规切数。所有记录均可自定义类型。', 9)

c = canvas.Canvas(str(OUT / 'cheki-diary-prd.pdf'), pagesize=(PAGE_W, PAGE_H))
c.setTitle('推活日记 产品需求与交互原型 v0.4')
c.setAuthor('Cheki Record')
c.setSubject('移动端产品原型、记录流程、统计规则与第一版验收标准')
page_number = 0

def text(x, y, value, size=11, color=INK):
    c.setFillColor(HexColor(color))
    c.setFont('CJK', size)
    c.drawString(x, y, value)

def para(value, x, y, width, size=11, leading=18, color=INK):
    style = ParagraphStyle('body', fontName='CJK', fontSize=size, leading=leading, textColor=HexColor(color), wordWrap='CJK')
    obj = Paragraph(escape(value).replace('\n', '<br/>'), style)
    _, h = obj.wrap(width, PAGE_H)
    if y - h < 40:
        raise RuntimeError(f'Content would overflow page {page_number}: {value[:50]}')
    obj.drawOn(c, x, y - h)
    return y - h

def line(x1, y1, x2, y2, color=LINE):
    c.setStrokeColor(HexColor(color)); c.setLineWidth(.6); c.line(x1, y1, x2, y2)

def panel(x, y, w, h, color='#efe8dc', radius=12):
    c.setFillColor(HexColor(color)); c.roundRect(x, y, w, h, radius, stroke=0, fill=1)

def new_page(kicker):
    global page_number
    if page_number:
        c.showPage()
    page_number += 1
    c.setFillColor(HexColor(PAPER)); c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    text(40, PAGE_H - 30, 'CHEKI DIARY  /  ' + kicker, 8, ROSE)
    line(40, 36, PAGE_W - 40, 36)
    text(40, 20, '推活日记 · 产品需求与交互原型 v0.4 · 2026.10.11', 8, MUTED)
    text(PAGE_W - 66, 20, f'{page_number:02d} / 14', 8, MUTED)

new_page('PRODUCT REQUIREMENTS')
text(48, 494, '推活日记', 43)
text(49, 456, '产品需求与交互原型', 23)
text(49, 414, '把见面的瞬间，好好留下。', 17, ROSE)
para('面向地下偶像粉丝的个人拍立得记录工具。\n以日期为主，活动随意填写；\n数量、金额和照片，各自清楚，又彼此关联。', 49, 369, 320, 12, 23, MUTED)
for i, t in enumerate(['快速记录 + 按日补录', '张数与花费双重统计', '可选照片 + 完整备份']):
    panel(49, 221 - i * 39, 290, 30, '#eee7dc', 6)
    text(62, 232 - i * 39, t, 11)
text(49, 88, '原型评审稿 v0.4', 10, ROSE)
text(49, 68, '平台待定 · 8 个页面 · 虚构演示数据', 10, MUTED)
for name, x, y, w in [('home', 401, 145, 164), ('quick', 609, 76, 177)]:
    h = w * 844 / 390
    panel(x-5, y-5, w+10, h+10, '#e1d9ce', 15)
    c.drawImage(str(SCREENS / f'{name}.png'), x, y, w, h)

new_page('SCOPE & FLOWS')
text(40, 518, '第一版先把记录这件事做好', 27)
para('确认范围：日期为主，活动选填；所有分类共用自定义单选类型；团切独立、特殊数量另记；照片与备份导出。', 41, 488, 740, 11, 18, MUTED)
for n, (title, body) in enumerate([
    ('日记', '月度概览与日期列表\n悬浮速记 / 按日补录\n当日明细与合计'),
    ('偶像', '个人 / 团体\n特殊 cheki 单独收藏\n按日期回顾'),
    ('相册', '可选上传\n按对象与特殊分类筛选\n照片关联原始记录'),
    ('统计', '月份 / 年份 / 全部\n日期与偶像分布\n待补金额提示'),
]):
    x = 40 + n * 195
    panel(x, 298, 176, 132, '#efe8de')
    text(x+16, 400, f'0{n+1}  {title}', 15, ROSE)
    para(body, x+16, 376, 148, 10.5, 20)
text(40, 265, '两条录入路径，都不依赖活动', 16)
para('现场：日期首页 → 默认今天 → 个人 / 团体 / 特殊、数量与金额 → 保存 → 当日记录\n事后：按日补录 → 选择日期 → 连续添加多人明细 → 核对新增合计 → 保存', 40, 243, 754, 12, 24)
line(40, 174, 800, 174)
para('先做 P0：独立记录、日期视图、对象与特殊统计。接着完成 P1：可选活动、类型、照片、相册及备份导出。P0 / P1 是开发顺序，全部属于第一版目标范围。', 40, 157, 355, 10.5, 19)
para('体验目标待真人验证：约 10 秒记一笔，3 位偶像的按日补录约 1 分钟完成。当前原型没有后端，不能保存真实收藏。', 443, 157, 355, 10.5, 19, MUTED)

for number, (key, title, subtitle, criteria, note) in enumerate(SCENES, 1):
    new_page(f'S{number:02d} / INTERACTION SPEC')
    image_w = 222
    c.drawImage(str(SCREENS / f'{key}.png'), 42, 54, image_w, image_w * 844 / 390)
    x = 305
    text(x, 518, title, 27)
    text(x, 490, subtitle, 12, ROSE)
    line(x, 471, 800, 471)
    m = re.search(rf'### S{number:02d} [^\n]+\n(.*?)(?=\n### |\n## |\Z)', SOURCE, re.S)
    bullets = [l[2:].strip() for l in m.group(1).splitlines() if l.startswith('- ')]
    y = 450
    for j, bullet in enumerate(bullets, 1):
        text(x, y-10, f'{j:02d}', 9, ROSE)
        y = para(bullet, x+26, y, 466, 10.3, 17) - 12
    line(x, 105, 799, 105)
    text(x, 89, '验收关联  ' + criteria, 9, ROSE)
    para(note, x, 76, 492, 9, 14, MUTED)

new_page('DATA & BUSINESS RULES')
text(40, 516, '常规与特殊，分别计数', 27)
text(41, 486, '日期由每笔记录独立保存，活动关联允许为空，照片直接关联记录。', 12, MUTED)
columns = [
    ('数据关系', [
        ('独立记录', '日期必填；关联对象和数量完整即可保存，类型单选自定义，活动可空。'),
        ('个人 / 团体', '常规只选一个对象；团切记在团体名下，不分摊给成员。'),
        ('可选活动', '作为补充标签。清除关联不删除记录，不改变日期或金额。'),
        ('照片', '直接关联独立记录，按其日期排列，不通过活动关联。'),
        ('自定义类型', '每笔最多一种，名称由用户配置；改名保持 ID，删除不删除记录。'),
    ]),
    ('统计约束', [
        ('张数', '常规切数 = 个人 + 团体；特殊数量另记，不按参与人数倍增。'),
        ('金额', '生产数据使用分为单位的整数；未填为 null，免费为 0。'),
        ('计算方式', '单价模式随数量重算；手动总额模式需要用户核对。'),
        ('统计日期', '使用记录实际日历日期；修改日期仅移动该笔，活动不约束日期。'),
        ('特殊 cheki', '特殊可关联多人，数量另记；不计个人或团体切数。花费只计一次。'),
    ]),
]
for n, (title, items) in enumerate(columns):
    x = 40 + n * 406
    text(x, 442, title, 16, ROSE)
    y = 414
    for name, desc in items:
        text(x, y, name, 11)
        y = para(desc, x, y-12, 352, 10.5, 18, MUTED) - 22
panel(40, 58, 761, 52, '#eee8de', 8)
para('恢复要求：先校验 → 预览数量和覆盖范围 → 明确确认 → 备份现状 → 原子恢复。\n恢复失败保留原数据，同一份备份重复恢复不增加记录；CSV 不代替完整备份。', 56, 96, 727, 10, 17)

new_page('ACCEPTANCE & NEXT DECISIONS')
text(40, 516, '验收与评审清单', 27)
text(41, 485, '以下是正式产品的验收标准；原型用于提前验证流程与信息层级。', 11, MUTED)
tests = [
    ('01', '活动空，录入 2/100、1/80、3/150', '6 张 / 330 元，不创建活动'),
    ('02', '新增 1 张，活动和金额都为空', '张数加 1，仅金额待补'),
    ('03', '实付填写 0 元', '不视为待补'),
    ('04', '单价 50 元，2 张改为 3 张', '金额变为 150 元'),
    ('05', '手动总额记录追加一张', '提示核对总额'),
    ('06', '无活动记录上传照片，再删除', '张数与金额不变'),
    ('07', '单笔记录日期改为上月', '移动该笔，相册重排'),
    ('08', '删除并撤销带照片记录', '明细与照片关联恢复'),
    ('09', '同日有活动与无活动混合', '全量汇总，日期只计一天'),
    ('10', '导出 CSV', '日期有值，活动允许空'),
    ('11', '含无活动照片记录的备份恢复两次', '不重复，空活动与照片保留'),
    ('12', '无效日期、小数张数、负金额', '阻止保存并指出错误'),
    ('13', '补填活动，再清除活动', '原记录身份与数值不变'),
    ('14', '删除某个活动', '保留记录，仅清除关联'),
    ('15', '先选 3寸，再选 宿题', '仅保留宿题，类型为单值'),
    ('16', '创建、改名、删除自定义类型', '记录数值和照片不受影响'),
]
y = 452
for idx, trigger, expect in tests:
    text(40, y, 'AC'+idx, 9, ROSE)
    para(trigger, 82, y+9, 277, 9.4, 14)
    para(expect, 368, y+9, 167, 9.4, 14, MUTED)
    line(40, y-18, 532, y-18)
    y -= 26
text(565, 452, '确认与待定的选择', 14, ROSE)
y = 424
for t in ['已确定：日期为主，活动选填。视觉风格与信息密度仍可讨论。', '已确定：类型完全自定义，每笔单选。用户可以直接命名为 3寸合照。', '已确定：团切单对象；特殊可关联多人，但数量不进入常规或个人切数。', '待评审：特殊花费计入总花费、不分摊个人的建议；平台与同步方式。']:
    y = para(t, 565, y, 235, 11, 20) - 20
line(565, 191, 800, 191)
para('原型边界\n当前内存演示，刷新后重置。CSV 可下载；ZIP 备份、真实恢复、服务端幂等、离线同步及云端照片存储尚未实现。', 565, 172, 235, 10, 18, MUTED)
for title, kicker, pics, subtitle, bullets, criteria in [
    ('团切：一个团体，一笔归属', 'GROUP RECORDS', ['quick-group','group'], '团体是记录对象，类型仍然可以自由配置。', [
        '常规记录选择团体后，仅关联一个团体，不同时关联成员。团体不要求先建立完整成员表。',
        '团切张数计入全局常规切数和该团体切数，不进入成员的个人切数；花费同理。',
        '个人、团体与特殊共享同一份自定义类型，每笔最多一条。主题团切、5寸等名称由用户自己配置。',
        '日期必填，活动和照片选填。团体拥有独立记录页、日期时间线与相册。',
    ], 'AC17：团切新增 2 张 / 100 元，类型为主题。全局与该团体各加 2 张，成员切数不变。'),
    ('特殊 cheki：同框，单独收藏', 'SPECIAL RECORDS', ['quick-special','special'], '可关联多位偶像，数量不计入总切数和个人切数。', [
        '特殊是独立记录分类，参与偶像可多选且去重，仅用于查找和回顾，不建立组合对象。',
        '常规切数只包含个人切与团切。特殊数量单列，不增加任何参与偶像或团体的切数。',
        '金额建议：特殊花费计入实际总花费一次，同时单列；不分摊给参与偶像。待产品评审确认。',
        '类型仍为自定义单选，与参与人数无关；普通合照类型不会自动转换为特殊分类。',
        '编辑分类时保留记录身份、日期、类型、照片与金额，清除无效关联并重新归类。',
    ], 'AC18–20：多人特殊不改变常规切数；分类转换只移动数量归属；导出恢复保留参与者且不重复计数。'),
]:
    new_page(kicker)
    text(40, 516, title, 27)
    text(41, 486, subtitle, 12, MUTED)
    for name, x in zip(pics,[43,224]):
        c.drawImage(str(SCREENS / f'{name}.png'), x, 95, 162, 162*844/390)
    y=444
    for idx, body in enumerate(bullets,1):
        text(420,y-10,f'{idx:02d}',9,ROSE)
        y=para(body,446,y,348,11,19)-20
    para(criteria,420,116,373,10,17,ROSE)
c.save()
print(f'Built 3 overview boards and {page_number}-page PDF: {OUT / "cheki-diary-prd.pdf"}')
