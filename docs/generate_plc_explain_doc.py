from pathlib import Path
import csv, io, re, html, zipfile
from datetime import datetime
root=Path.cwd(); docs=root/'docs'; main=root/'plc_ctrvina'/'MAIN.csv'; comment=root/'plc_ctrvina'/'COMMENT.csv'; logo=root/'ui'/'logo.jpg'
out_md=docs/'PLC_MAIN_CODE_EXPLAIN_CTRVINA.md'; out_docx=docs/'PLC_MAIN_CODE_EXPLAIN_CTRVINA.docx'
SEC=re.compile(r'^\d{2}(?:\.\d+)?\s+')
def read(p): return p.read_text(encoding='utf-16le',errors='replace').lstrip('\ufeff')
def rows(p): return list(csv.reader(io.StringIO(read(p)),delimiter='\t'))
def clean(s): return re.sub(r'\s+',' ',s.strip())
cm={}
for r in rows(comment)[2:]:
    if len(r)>=2 and r[0].strip(): cm[r[0].strip().upper()]=clean(r[1])
comments=sorted(cm.items(), key=lambda x:(x[0][0], int(re.sub(r'\D','',x[0]) or 0), x[0]))
# B? sung ? ngh?a cho c?c M n?i b? m?i c? trong MAIN.csv nh?ng COMMENT.csv ch?a m? t?.
cm.setdefault('M110', 'L?nh Jog chi?u d??ng ?? ???c PLC x?c nh?n t? D110=1')
cm.setdefault('M111', 'L?nh Jog chi?u ?m ?? ???c PLC x?c nh?n t? D111=1')
cm.setdefault('M112', 'L?nh Home/v? g?c ?? ???c PLC x?c nh?n t? D112=1')
sections=[]; cur=None; last=''
for r in rows(main)[3:]:
    step=r[0].strip() if len(r)>0 else ''; stmt=r[1].strip() if len(r)>1 else ''; inst=r[2].strip() if len(r)>2 else ''; dev=r[3].strip() if len(r)>3 else ''
    if step: last=step
    if stmt and not inst and not dev:
        if SEC.match(stmt):
            cur={'step':step or last,'title':stmt,'notes':[],'cmds':[]}; sections.append(cur)
        elif cur: cur['notes'].append(stmt)
        continue
    if inst or dev:
        if not cur:
            cur={'step':step or last,'title':'00 Cac lenh dau chuong trinh','notes':[],'cmds':[]}; sections.append(cur)
        cur['cmds'].append((step or last,inst,dev))

def base(d): return d.upper().split('.')[0]
def devs(cmds):
    a=[]
    for _,_,d in cmds:
        for tok in re.findall(r'\b[XYMDTCS]\d+(?:\.\d+)?\b',d.upper()):
            b=tok.split('.')[0]
            if b not in a: a.append(b)
    return a
def rng(sec):
    nums=[int(s) for s,_,_ in sec['cmds'] if str(s).isdigit()]
    return f"Dòng/Step {min(nums)} - {max(nums)}" if nums else f"Step {sec['step']}"
def collect_args(cmds, idx):
    args=[]; j=idx+1
    while j < len(cmds) and not cmds[j][1].strip() and cmds[j][2].strip():
        args.append(cmds[j][2]); j += 1
    return args, j

def ladder(sec):
    out=[]; idx=0; cmds=sec['cmds']
    while idx < len(cmds):
        st,ins,d=cmds[idx]; i=ins.upper().strip()
        if not i:
            idx += 1; continue
        args, nxt = collect_args(cmds, idx)
        if i in ('LD','LDI','LDP','AND','ANI','OR'):
            sym='| |' if i not in ('LDI','ANI') else '|/|'
            if i=='LDP': sym='|P|'
            extra = (' ' + ' '.join(args)) if args else ''
            out.append(f"{st:>5} ---{sym}--- {ins} {d}{extra:<10}  {cm.get(base(d),'')}")
        elif i in ('LD=','AND=','AND<=','AND<','AND>','AND>=','LD<','LD>'):
            extra = (' ' + ' '.join(args)) if args else ''
            out.append(f"{st:>5} ---[ {ins} {d}{extra} ]---  {cm.get(base(d),'')}")
        elif i in ('OUT','SET','RST','ALT'):
            coil={'OUT':'OUT','SET':'SET','RST':'RST','ALT':'ALT'}[i]
            out.append(f"{st:>5} -----------------------------({coil} {d})  {cm.get(base(d),'')}")
        elif i in ('MOV','DMOV','ADD','SUB','DSUB','MUL','DMUL','DDIV','NEG','PLSY','DPLSV'):
            all_args=[d]+args
            out.append(f"{st:>5} [{i} {' -> '.join(all_args)}]")
        else:
            out.append(f"{st:>5} [{i} {d}]".rstrip())
        idx = nxt
    return '\n'.join(out[:90])

def meaning(title):
    t=title.lower()
    pairs=[('modbus','Khởi tạo truyền thông Modbus RTU Slave cho FX3U/FX3UC: cấu hình tốc độ, protocol, delay, Slave ID và vùng thanh ghi D cho PC truy cập.'),('tach','Đọc word/lệnh PC và tách thành các M trung gian để PLC xử lý START/STOP/ghi đo/jog/home.'),('tra trang thai','Ghi trạng thái máy về PC qua các thanh ghi D131..D134 để phần mềm biết xi lanh, servo, done và quyền ghi mẫu.'),('den bao','Điều khiển các đèn/ngõ ra báo trạng thái RUN, STOP hoặc lỗi.'),('run stop','Tạo mạch tự giữ RUN M0; START từ nút vật lý/PC, STOP bởi nút Stop, EMG hoặc Abort.'),('servo on','Bật ngõ ra Servo ON Y005 khi hệ thống RUN và điều kiện an toàn hợp lệ.'),('kep','Toggle kẹp/nhả xi lanh bằng hai nút an toàn hoặc lệnh PC.'),('bat dau do','Khởi tạo chu trình đo: set đang đo, cho ghi dữ liệu, reset Done, nạp mode và reset góc/cycle.'),('dung do','Dừng chu trình đo và đưa hệ thống về trạng thái hoàn tất.'),('brake','Nhả phanh servo ngay khi đo và khóa lại khi không đo.'),('chu trinh goc','Thiết lập phase chung cho chu trình điều khiển góc.'),('target','Sinh góc đích theo chuỗi 0 → góc dương → 0 → góc âm → 0.'),('skip zero','Bỏ qua step nếu góc đặt bằng 0.'),('manual','Chế độ Manual/Jog/Home khi không chạy test.'),('clear calculations','Xóa các thanh ghi tính toán khi không test.'),('sai lech','Tính sai lệch góc, số xung cần phát và chiều servo.'),('cap nhat goc hien thi','Cập nhật góc hiện tại từ xung phát/encoder để PC hiển thị.'),('advance','Chuyển bước khi đã tới target.'),('step4 ve 0 xong va chua du','Tăng cycle và quay lại step 1 khi chưa đủ số chu kỳ.'),('step4 ve 0 xong va du','Kết thúc test khi đủ số chu kỳ.'),('step3','Từ góc âm về 0.'),('step2','Từ 0 chuyển sang góc âm.'),('step1','Từ góc dương về 0.'),('current cycle','Cập nhật chu kỳ hiện tại.'),('clear done','PC xóa cờ DONE.'),('reset d100','Reset word lệnh PC cuối scan.')]
    for k,v in pairs:
        if k in t: return v
    return 'Cụm logic xử lý vận hành PLC trong MAIN.csv.'
def explain_cmd(sec):
    res=[]; cmds=sec['cmds']; idx=0
    while idx<len(cmds):
        st,ins,d=cmds[idx]; i=ins.upper().strip()
        if not i: idx+=1; continue
        args=[d]; j=idx+1
        while j<len(cmds) and not cmds[j][1].strip() and cmds[j][2].strip(): args.append(cmds[j][2]); j+=1
        txt=''
        if i in ('LD','LDI','LDP','AND','ANI','OR'):
            txt=f"{ins} {d}: dùng {cm.get(base(d),'thiết bị/thanh ghi '+d)} làm điều kiện logic."
        elif i in ('LD=','AND=','AND<=','AND<','AND>','AND>=','LD<','LD>','LD<='):
            right = args[1] if len(args) > 1 else ''
            op_map={'LD=':'bằng','AND=':'bằng','AND<=':'nhỏ hơn hoặc bằng','AND<':'nhỏ hơn','AND>':'lớn hơn','AND>=':'lớn hơn hoặc bằng','LD<':'nhỏ hơn','LD>':'lớn hơn','LD<=':'nhỏ hơn hoặc bằng'}
            txt=f"{ins} {' '.join(args)}: kiểm tra {args[0]} ({cm.get(base(args[0]),'thanh ghi/thiết bị')}) {op_map.get(i,'so sánh')} {right}; đúng thì cho phép nhánh logic tiếp tục."
        elif i in ('OUT','SET','RST','ALT'):
            txt=f"{ins} {d}: tác động lên {d} - {cm.get(base(d),'device nội bộ/ngõ ra')}."
        elif i in ('MOV','DMOV') and len(args)>=2:
            txt=f"{ins} {args[0]} {args[1]}: ghi/copy giá trị {args[0]} vào {args[1]} ({cm.get(base(args[1]),'thanh ghi đích')})."
        elif i in ('ADD','SUB','DSUB','MUL','DMUL','DDIV'):
            txt=f"{ins} {' '.join(args)}: phép tính phục vụ tính góc/xung/chuyển bước."
        elif i == 'NEG':
            txt=f"NEG {args[0]}: đổi dấu giá trị trong {args[0]} ({cm.get(base(args[0]),'thanh ghi')})."
        elif i == 'END':
            txt="END: kết thúc chương trình, lặp lại từ đầu."
        elif i in ('PLSY','DPLSV'):
            txt=f"{ins} {' '.join(args)}: phát xung servo theo tốc độ/số xung và ngõ ra chỉ định."
        elif i in ('MPS','MRD','MPP','ANB'):
            txt=f"{ins}: lệnh chia/ghép nhánh ladder để dùng chung điều kiện trước đó."
        else: txt=f"{ins} {' '.join(args)}: lệnh xử lý trong cụm."
        if txt not in res: res.append(txt)
        idx=j
    return res
# markdown
md=['# GIẢI THÍCH CODE PLC MAIN.csv THEO TỪNG CỤM / TỪNG DÒNG','','Khách hàng: CÔNG TY CTR VINA','','Phiên bản tài liệu: 1.0','',f'Ngày biên soạn: {datetime.now():%d/%m/%Y}','','Tài liệu này đọc lại từ file MAIN.csv mới nhất. Format giữ theo dạng giải thích cụm: sơ đồ ladder/text, ý nghĩa thanh ghi và tác dụng cụm.','','## BẢNG COMMENT THIẾT BỊ / THANH GHI','','| Device | Ý nghĩa |','| --- | --- |']
for d,c in comments: md.append(f'| {d} | {c} |')
md.append('')
for n,sec in enumerate(sections,1):
    md += [f'## PHẦN {n}: {sec["title"]}','', '```text', f'{rng(sec)}: {meaning(sec["title"])}', '```','', '### Sơ đồ Ladder:', '```text', ladder(sec), '```']
    if sec['notes']: md += ['','### Ghi chú trong MAIN.csv:']+[f'- {x}' for x in sec['notes']]
    md += ['','### Thanh ghi / thiết bị liên quan:','','| Device | Ý nghĩa trong cụm |','| --- | --- |']
    for d in devs(sec['cmds']): md.append(f'| {d} | {cm.get(d,"Dùng trong logic cụm này")} |')
    md += ['','### Giải thích:']+[f'- {x}' for x in explain_cmd(sec)]+['','---','']
out_md.write_text('\n'.join(md),encoding='utf-8')
# docx minimal from md lines
W=[]
def esc(x): return html.escape(str(x),quote=False)
def p(t='',style=None,align=None,b=False,font=None):
    rpr=''.join(['<w:b/>' if b else '', f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>' if font else ''])
    ppr=(f'<w:pStyle w:val="{style}"/>' if style else '')+(f'<w:jc w:val="{align}"/>' if align else '')
    return f'<w:p>{("<w:pPr>"+ppr+"</w:pPr>") if ppr else ""}<w:r>{("<w:rPr>"+rpr+"</w:rPr>") if rpr else ""}<w:t xml:space="preserve">{esc(t)}</w:t></w:r></w:p>'
def br(): return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
def cell(t,w='2500',bold=False): return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr>{p(t,b=bold)}</w:tc>'
def tbl(headers,rs,widths):
    x=['<w:tbl><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/><w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/><w:insideH w:val="single" w:sz="4"/><w:insideV w:val="single" w:sz="4"/></w:tblBorders></w:tblPr>']
    x.append('<w:tr>'+''.join(cell(h,widths[i],True) for i,h in enumerate(headers))+'</w:tr>')
    for r in rs: x.append('<w:tr>'+''.join(cell(str(r[i]),widths[i]) for i in range(len(headers)))+'</w:tr>')
    return ''.join(x)+ '</w:tbl>'
img=''; relx=''; ctx=''; media=[]
if logo.exists():
    media=[('word/media/logo.jpg',logo)]; relx='<Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.jpg"/>'; ctx='<Default Extension="jpg" ContentType="image/jpeg"/>'
    img='''<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><wp:extent cx="4572000" cy="914400"/><wp:docPr id="1" name="Logo"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="logo.jpg"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:embed="rIdLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="4572000" cy="914400"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''
body=[img,p('GIẢI THÍCH CODE PLC',align='center',b=True),p('MAIN.csv - CÔNG TY CTR VINA',align='center',b=True),p('Phiên bản 1.0 - '+datetime.now().strftime('%d/%m/%Y'),align='center'),br(),p('BẢNG COMMENT THIẾT BỊ / THANH GHI','Heading1'),tbl(['Device','Ý nghĩa'],comments,['1800','7200']),br()]
for n,sec in enumerate(sections,1):
    body += [p(f'PHẦN {n}: {sec["title"]}','Heading1'),p(f'{rng(sec)}: {meaning(sec["title"])}',font='Consolas'),p('Sơ đồ Ladder:','Heading2'),p(ladder(sec),font='Consolas')]
    if sec['notes']:
        body.append(p('Ghi chú trong MAIN.csv:','Heading2'))
        for x in sec['notes']: body.append(p('• '+x))
    body += [p('Thanh ghi / thiết bị liên quan:','Heading2'),tbl(['Device','Ý nghĩa trong cụm'],[(d,cm.get(d,'Dùng trong logic cụm này')) for d in devs(sec['cmds'])],['1800','7200']),p('Giải thích:','Heading2')]
    for x in explain_cmd(sec): body.append(p('• '+x))
styles='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="32"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:rPr><w:b/><w:color w:val="2F75B5"/><w:sz w:val="26"/></w:rPr></w:style></w:styles>'''
doc=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>{''.join(body)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'''
ct=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>{ctx}<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
drels=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>{relx}</Relationships>'''
with zipfile.ZipFile(out_docx,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml',ct); z.writestr('_rels/.rels',rels); z.writestr('word/_rels/document.xml.rels',drels); z.writestr('word/document.xml',doc); z.writestr('word/styles.xml',styles)
    for a,s in media: z.write(s,a)
print(out_md); print(out_docx); print('Sections:',len(sections),'Comments:',len(comments))
