"""Núcleo local: uma fonte por arquivo, escrita Windows com exclusão de compartilhamento."""
import ctypes, hashlib, json, msvcrt, os, re, sqlite3, time, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

HOME=Path(__file__).resolve().parent.parent
REAL_VAULT=Path(os.environ.get('EMC_VAULT',str(HOME/'meu-cofre'))).resolve()
REAL_SYSTEM=Path(os.environ.get('EMC_SYSTEM',str(HOME))).resolve()
def config_file(root,name):
    root=Path(root); direct=root/name; cfg=root/'config'/name
    return direct if direct.exists() or not cfg.exists() else cfg
NOW=lambda:datetime.now(timezone.utc).isoformat(timespec='seconds')
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'))
class Conflict(Exception): pass
class Uncertain(Exception): pass
class Locked(Exception): pass
class Invalid(Exception): pass

def exclusive(path,create=False,delete=False):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
    kernel.CreateFileW.restype=ctypes.c_void_p
    h=kernel.CreateFileW(str(path),0x80000000|0x40000000|(0x00010000 if delete else 0),0,None,1 if create else 3,0x80,None)
    if h==ctypes.c_void_p(-1).value:
        err=ctypes.get_last_error()
        if err in (32,33): raise Locked('arquivo ocupado; nenhuma escrita aplicada')
        raise OSError(err,'não foi possível abrir arquivo com exclusividade')
    try: fd=msvcrt.open_osfhandle(h,os.O_RDWR|os.O_BINARY)
    except Exception: kernel.CloseHandle(ctypes.c_void_p(h)); raise
    return os.fdopen(fd,'r+b')

READ_BACKOFF=(0.01,0.025,0.05,0.1)

def acquire_content(path,create=False,delete=False):
    """Repete só a aquisição em Locked; retorna uma vez, antes de executar qualquer corpo."""
    for attempt in range(len(READ_BACKOFF)+1):
        try:return exclusive(path,create=create,delete=delete)
        except Locked:
            if attempt==len(READ_BACKOFF):raise
            time.sleep(READ_BACKOFF[attempt])


def read_exclusive(path):
    with acquire_content(path) as stream:return stream.read()

def render(n):
    common=['id','record_type','schema_version','revision','title','created_at','updated_at','created_by','access_policy_ref','lifecycle_status','payload_format']
    return ('---\n'+''.join(k+': '+json.dumps(n[k],ensure_ascii=False)+'\n' for k in common)+'---\n```brain-json\n'+json.dumps(n['payload'],ensure_ascii=False,indent=2)+'\n```\n').encode('utf-8')
def parse(b):
    m=re.match(r'\A---\n(.*?)\n---\n```brain-json\n(.*?)\n```\n\Z',b.decode('utf-8'),re.S)
    if not m:raise Invalid('nota não corresponde ao formato controlado')
    h={}
    for line in m.group(1).splitlines():
        k,sep,v=line.partition(': ')
        if not sep or k in h:raise Invalid('cabeçalho inválido')
        h[k]=json.loads(v)
    h['payload']=json.loads(m.group(2)); return h

def filename(title,ident,existing):
    t=re.sub(r'[<>:"/\\|?*\x00-\x1f]',' ',title).strip(' .')
    t=re.sub(r'\s+',' ',t)[:90].rstrip(' .')
    if not t or t.upper() in {'CON','PRN','AUX','NUL','COM1','LPT1'}: t='Fonte'
    name=t+'.md'
    if name.casefold() in {x.casefold() for x in existing}: name=f'{t} — {ident[:8]}.md'
    return name

class Store:
    def __init__(self,root=REAL_SYSTEM,vault=REAL_VAULT):
        self.root=Path(root).resolve(); self.vault=Path(vault).resolve()
        temp=(REAL_SYSTEM/'testes_temporarios').resolve()
        if not ((self.root==REAL_SYSTEM and self.vault==REAL_VAULT) or (temp in self.root.parents and temp in self.vault.parents)):
            raise Invalid('raiz fora do escopo autorizado')
        self.folder=self.vault/'30_Fontes'; self.hist=self.root/'estado'/'revisoes'; self.db=self.root/'estado'/'controle.sqlite3'
        for p in (self.folder,self.hist,self.db.parent):p.mkdir(parents=True,exist_ok=True)
        if self.folder.resolve().parent!=self.vault or self.hist.resolve().parent.parent!=self.root:raise Invalid('caminho redirecionado')
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, filename TEXT UNIQUE, revision INTEGER, digest TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS tombstones(record_id TEXT PRIMARY KEY, operation_key TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS operations(key TEXT PRIMARY KEY, fingerprint TEXT, status TEXT, record_id TEXT, expected INTEGER, filename TEXT, old_digest TEXT, new_digest TEXT, pending BLOB, result TEXT)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.db,timeout=15); c.execute('PRAGMA synchronous=FULL'); c.execute('PRAGMA secure_delete=ON')
        try:
            with c:yield c
        finally:c.close()
    def safe_path(self,name):
        p=(self.folder/name).resolve()
        if p.parent!=self.folder.resolve() or p.name!=name or p.is_symlink(): raise Invalid('caminho fora da pasta controlada')
        return p
    def status(self,key):
        with self.connect() as c:r=c.execute('SELECT status,result FROM operations WHERE key=?',(key,)).fetchone()
        return {'status':'unknown'} if not r else {'status':r[0],'result':json.loads(r[1]) if r[1] else None}
    def read(self,ident):
        with self.connect() as c:
            if c.execute('SELECT 1 FROM tombstones WHERE record_id=?',(ident,)).fetchone():raise Invalid('registro excluído ou em exclusão')
            r=c.execute('SELECT filename,revision,digest FROM records WHERE id=?',(ident,)).fetchone()
        if not r:raise Invalid('registro não encontrado')
        b=read_exclusive(self.safe_path(r[0]))
        if sha(b)!=r[2]:raise Conflict('edição externa detectada; reconciliação necessária')
        n=parse(b)
        if n['id']!=ident or n['revision']!=r[1]:raise Conflict('identidade ou revisão divergente')
        return n
    def list(self):
        with self.connect() as c:ids=[r[0] for r in c.execute('SELECT id FROM records WHERE id NOT IN (SELECT record_id FROM tombstones) ORDER BY filename').fetchall()]
        return [{'id':n['id'],'title':n['title'],'revision':n['revision']} for n in (self.read(i) for i in ids)]
    def _validate_parent(self,c,ref,ident):
        if ref['record_id']==ident:raise Invalid('fonte não pode ser sua própria origem')
        if c.execute('SELECT 1 FROM tombstones WHERE record_id=?',(ref['record_id'],)).fetchone():
            raise Invalid('fonte de origem excluída ou em exclusão')
        row=c.execute('SELECT filename,revision,digest FROM records WHERE id=?',(ref['record_id'],)).fetchone()
        if not row:raise Invalid('fonte de origem inexistente')
        if ref['revision']!=row[1]:raise Conflict('revisão da fonte de origem desatualizada')
        data=read_exclusive(self.safe_path(row[0]))
        if sha(data)!=row[2]:raise Conflict('fonte de origem alterada externamente')
        parent=parse(data)
        if parent.get('record_type')!='source' or parent.get('id')!=ref['record_id'] or parent.get('revision')!=row[1]:
            raise Conflict('identidade ou revisão da fonte de origem divergente')

    def apply(self,key,kind,title='',text='',ident='',expected=0,reason='',source_metadata=None):
        if not re.fullmatch('[A-Za-z0-9_-]{1,80}',key):raise Invalid('chave inválida')
        if kind not in ('create','correct') or not text.strip() or len(text)>20000:raise Invalid('conteúdo ou operação inválidos')
        if kind=='create' and (not title.strip() or len(title)>120):raise Invalid('título inválido')
        if kind=='correct' and (not reason.strip() or len(reason)>500):raise Invalid('motivo de correção obrigatório')
        req={'kind':kind,'title':title,'text':text,'id':ident,'expected':expected,'reason':reason}
        if source_metadata is not None:
            from documentos import validate_metadata
            source_metadata=validate_metadata(source_metadata)
            req['source_metadata']=source_metadata
        fingerprint=sha(canon(req).encode())
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE'); op=c.execute('SELECT fingerprint,status,result,record_id FROM operations WHERE key=?',(key,)).fetchone()
            if op:
                if op[0]!=fingerprint:raise Conflict('chave reutilizada para outro pedido')
                if c.execute('SELECT 1 FROM tombstones WHERE record_id=?',(op[3],)).fetchone():raise Invalid('registro excluído ou em exclusão')
                if op[1]=='confirmed':return json.loads(op[2])
            else:
                if kind=='create':
                    ident=str(uuid.uuid4()); expected=0; title=title.strip()
                    names=([r[0] for r in c.execute('SELECT filename FROM records').fetchall()]
                           +[r[0] for r in c.execute("SELECT filename FROM operations WHERE status!='confirmed' AND filename IS NOT NULL").fetchall()]
                           +[p.name for p in self.folder.glob('*.md')])
                    name=filename(title,ident,names); oldhash=None; created=NOW()
                    n={'id':ident,'record_type':'source','schema_version':'0.1','revision':1,'title':title,'created_at':created,'updated_at':created,'created_by':'ponte_local','access_policy_ref':'proprietario_local','lifecycle_status':'active','payload_format':'brain_json_v1','payload':{'source_kind':'conversation','origin_description':'Relato fornecido à ponte pelo usuário','received_at':created,'availability_status':'retained','retention_conditions':'cofre pessoal local','content_locator':'payload.content','content':text}}
                else:
                    r=c.execute('SELECT filename,revision,digest FROM records WHERE id=?',(ident,)).fetchone()
                    if not r or type(expected)!=int or r[1]!=expected:raise Conflict('revisão esperada não corresponde')
                    name,_,oldhash=r
                    old=read_exclusive(self.safe_path(name))
                    if sha(old)!=oldhash:raise Conflict('edição externa detectada')
                    n=parse(old); n['revision']=expected+1; n['updated_at']=NOW(); n['payload']['content']=text; n['payload']['correction']={'previous_revision':expected,'reason':reason.strip(),'corrected_at':n['updated_at']}
                if source_metadata is not None:
                    parent=source_metadata.get('parent_source_ref')
                    # Uma origem já registrada pode apontar uma revisão histórica legítima.
                    if parent is not None and (kind=='create' or parent!=n['payload'].get('parent_source_ref')):
                        self._validate_parent(c,parent,ident)
                    n['payload'].update(source_metadata)
                data=render(n); newhash=sha(data)
                c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?,?,?,?)',(key,fingerprint,'proposed',ident,expected,name,oldhash,newhash,data,None))
        return self.finish(key)
    def finish(self,key):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE'); op=c.execute('SELECT status,record_id,expected,filename,old_digest,new_digest,pending,result FROM operations WHERE key=?',(key,)).fetchone()
            if not op:raise Invalid('operação desconhecida')
            status,ident,expected,name,oldhash,newhash,data,result=op
            if c.execute('SELECT 1 FROM tombstones WHERE record_id=?',(ident,)).fetchone():raise Invalid('registro excluído ou em exclusão')
            if status=='confirmed':return json.loads(result)
            row=c.execute('SELECT revision,digest FROM records WHERE id=?',(ident,)).fetchone()
            path=self.safe_path(name)
            if expected==0 and row is None and not path.exists():
                f=acquire_content(path,create=True)
            else:
                if not path.exists():raise Uncertain('arquivo ausente; reconciliar antes de repetir')
                f=acquire_content(path)
            with f:
                old=f.read(); current=sha(old)
                if current==newhash:
                    pass # efeito anterior aplicado; confirmação perdida
                else:
                    if expected==0:
                        if old:raise Uncertain('criação parcial ou arquivo inesperado')
                    elif row!=(expected,oldhash) or current!=oldhash:
                        raise Conflict('revisão ou arquivo mudou; não sobrescrito')
                    if expected:
                        hist=(self.hist/ident); hist.mkdir(exist_ok=True); dest=hist/(str(expected)+'.md')
                        if dest.exists() and sha(dest.read_bytes())!=oldhash:raise Conflict('histórico divergente')
                        if not dest.exists():
                            with dest.open('xb') as h:h.write(old);h.flush();os.fsync(h.fileno())
                    f.seek(0); f.write(data); f.truncate(); f.flush(); os.fsync(f.fileno())
            result={'status':'confirmed','id':ident,'revision':expected+1}
            if row is None:c.execute('INSERT INTO records VALUES(?,?,?,?)',(ident,name,expected+1,newhash))
            else:c.execute('UPDATE records SET revision=?,digest=? WHERE id=?',(expected+1,newhash,ident))
            c.execute('UPDATE operations SET status=?,pending=NULL,result=? WHERE key=?',('confirmed',json.dumps(result),key))
            return result

    def delete(self,key,ident,expected):
        if not re.fullmatch('[A-Za-z0-9_-]{1,80}',key) or type(expected)!=int or expected<1:raise Invalid('pedido de exclusão inválido')
        fingerprint=sha(canon({'kind':'delete','id':ident,'expected':expected}).encode())
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            op=c.execute('SELECT fingerprint,status,result FROM operations WHERE key=?',(key,)).fetchone()
            if op:
                if op[0]!=fingerprint:raise Conflict('chave reutilizada para outro pedido')
                if op[1]=='confirmed':return json.loads(op[2])
            else:
                if c.execute('SELECT 1 FROM tombstones WHERE record_id=?',(ident,)).fetchone():raise Invalid('registro já está em exclusão')
                row=c.execute('SELECT filename,revision,digest FROM records WHERE id=?',(ident,)).fetchone()
                if not row or row[1]!=expected:raise Conflict('revisão esperada não corresponde')
                c.execute('INSERT INTO tombstones VALUES(?,?)',(ident,key))
                c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?,?,?,?)',(key,fingerprint,'proposed',ident,expected,row[0],row[2],None,None,None))
        # O tombstone já foi confirmado: leituras e operações anteriores não servem a fonte.
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            status,name,oldhash,result=c.execute('SELECT status,filename,old_digest,result FROM operations WHERE key=?',(key,)).fetchone()
            if status=='confirmed':return json.loads(result)
            path=self.safe_path(name)
            if path.exists():
                with acquire_content(path,delete=True) as f:
                    if sha(f.read())!=oldhash:raise Conflict('arquivo alterado durante exclusão; não removido')
                    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                    kernel.SetFileInformationByHandle.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32]
                    kernel.SetFileInformationByHandle.restype=ctypes.c_int
                    disposition=ctypes.c_ubyte(1)
                    if not kernel.SetFileInformationByHandle(ctypes.c_void_p(msvcrt.get_osfhandle(f.fileno())),4,ctypes.byref(disposition),ctypes.sizeof(disposition)):
                        raise OSError(ctypes.get_last_error(),'não foi possível marcar arquivo para exclusão')
            hist=self.hist/ident
            if hist.exists():
                if hist.is_symlink() or hist.resolve().parent!=self.hist.resolve():raise Invalid('histórico fora do escopo')
                for p in hist.iterdir():
                    if p.is_symlink() or not p.is_file() or not re.fullmatch(r'[1-9][0-9]*\.md',p.name):raise Invalid('arquivo inesperado no histórico')
                    p.unlink()
                hist.rmdir()
            c.execute('UPDATE operations SET pending=NULL WHERE record_id=?',(ident,))
            c.execute('DELETE FROM records WHERE id=?',(ident,))
            result={'status':'confirmed','id':ident,'effect':'excluded_from_controlled_store'}
            c.execute('UPDATE operations SET status=?,result=? WHERE key=?',('confirmed',json.dumps(result),key))
            return result
