from pathlib import Path
import zipfile, html, re
from datetime import datetime
root=Path.cwd()
src=root/'plc_ctrvina'/'PLC_MAIN_CODE_EXPLAIN.md'
docs=root/'docs'
docs.mkdir(exist_ok=True)
out_md=docs/'PLC_MAIN_CODE_EXPLAIN_CTRVINA.md'
out_docx=docs/'PLC_MAIN_CODE_EXPLAIN_CTRVINA.docx'
text=src.read_text(encoding='utf-8')
# Add customer-facing cover note if missing
cover = f'''# GIẢI THÍCH CODE PLC MAIN.csv THEO TỪNG CỤM / TỪNG DÒNG\n\nKhách hàng: CÔNG TY CTR VINA\n\nPhiên bản tài liệu: 1.0\n\nNgày biên soạn: {datetime.now().strftime('%d/%m/%Y')}\n\nTài liệu này dùng để giải thích logic PLC trong file MAIN.csv theo từng cụm lệnh, từng nhóm dòng và ý nghĩa vận hành. Tài liệu phục vụ kỹ thuật PLC/bảo trì, không phải tài liệu source code phần mềm PC.\n\n---\n\n'''
# remove old title first line to avoid duplicate
body='\n'.join(text.splitlines()[1:])
out_md.write_text(cover+body, encoding='utf-8')

def esc(s): return html.escape(s, quote=False)
def run(t,b=False,size=None):
    props=''
    if b or size:
        props='<w:rPr>'+('<w:b/>' if b else '')+(f'<w:sz w:val="{size}"/>' if size else '')+'</w:rPr>'
    return f'<w:r>{props}<w:t xml:space="preserve">{esc(t)}</w:t></w:r>'
def p(t='',style=None):
    ppr=f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ''
    return f'<w:p>{ppr}{run(t)}</w:p>'
def heading(t,l): return p(t, f'Heading{min(l,3)}')
def code_line(t): return f'<w:p><w:pPr><w:pStyle w:val="Code"/></w:pPr>{run(t)}</w:p>'
def bullet(t): return p('• '+t)
def page_break(): return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

parts=[]
in_code=False
for line in (cover+body).splitlines():
    if line.startswith('```'):
        in_code=not in_code; continue
    if in_code:
        parts.append(code_line(line)); continue
    m=re.match(r'^(#{1,6})\s+(.*)', line)
    if m:
        parts.append(heading(m.group(2), len(m.group(1)))); continue
    if line.strip()=='---':
        parts.append(p('')) ; continue
    if line.startswith('*   ') or line.startswith('- '):
        parts.append(bullet(line.replace('*   ','',1).replace('- ','',1))); continue
    if line.strip(): parts.append(p(line.strip()))
    else: parts.append(p(''))

document=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{''.join(parts)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'''
styles='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="Arial"/><w:sz w:val="22"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="32"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="2F75B5"/><w:sz w:val="26"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="5B9BD5"/><w:sz w:val="24"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/></w:rPr></w:style></w:styles>'''
ct='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
drels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
with zipfile.ZipFile(out_docx,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml',ct); z.writestr('_rels/.rels',rels); z.writestr('word/_rels/document.xml.rels',drels); z.writestr('word/document.xml',document); z.writestr('word/styles.xml',styles)
print(out_md)
print(out_docx)
