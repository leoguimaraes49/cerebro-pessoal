"""Busca lexical, semântica local e grafo; cache vinculado à geração observada."""
import hashlib,json,sqlite3
from pathlib import Path
from contextlib import contextmanager
from nucleo import Invalid,Conflict,canon,sha,NOW
from conhecimento import Knowledge,refs


class LocalEmbeddings:
    def __init__(self,folder):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.np=__import__('numpy');folder=Path(folder)
        checks={'model.onnx':'ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665',
                'tokenizer.json':'0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39'}
        for name,digest in checks.items():
            if sha((folder/name).read_bytes())!=digest:raise Invalid('modelo local diferente da revisão validada')
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(folder/'model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        self.tokenizer=Tokenizer.from_file(str(folder/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=256,stride=32);self.tokenizer.enable_padding()
    def chunks(self,text,kind='passage'):
        np=self.np;encoding=self.tokenizer.encode(kind+': '+text)
        encodings=[encoding]+encoding.overflowing;vectors=[]
        for e in encodings:
            ids=np.array([e.ids],dtype=np.int64);mask=np.array([e.attention_mask],dtype=np.int64)
            candidates={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.array([e.type_ids],dtype=np.int64)}
            output=self.session.run(None,{i.name:candidates[i.name] for i in self.session.get_inputs()})[0]
            vector=(output*mask[:,:,None]).sum(axis=1)/np.maximum(mask.sum(axis=1)[:,None],1)
            vector=vector/np.maximum(np.linalg.norm(vector,axis=1,keepdims=True),1e-12)
            vectors.append(vector[0].astype(np.float32).tolist())
        return vectors


class Retrieval:
    def __init__(self,sources,embedder=None,scope='proprietario_local'):
        self.sources=sources;self.k=Knowledge(sources);self.embedder=embedder;self.scope=scope
        self.db=sources.root/'estado'/'recuperacao.sqlite3'
        with self.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS vectors(id TEXT,part INTEGER,digest TEXT,value TEXT,PRIMARY KEY(id,part));
              CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);
              CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,generation TEXT,result TEXT);
              CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,query TEXT,generation TEXT,reused INTEGER,result_ids TEXT);
              CREATE TABLE IF NOT EXISTS recipes(key TEXT PRIMARY KEY,query TEXT,steps TEXT,uses INTEGER,last_generation TEXT);''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.db,timeout=30)
        try:
            with c:yield c
        finally:c.close()
    def snapshot(self):
        records,_,issues=self.k.catalog();invalid=self.k.stale(records)
        generation=sha(canon({'records':records,'issues':issues,'scope':self.scope}).encode())
        return generation,records,invalid,issues
    def search(self,query,limit=12,depth=1):
        if not isinstance(query,str) or not query.strip() or len(query)>500 or type(limit)is not int or not 1<=limit<=50 or type(depth)is not int or not 0<=depth<=2:
            raise Invalid('consulta fora dos limites')
        generation,records,invalid,issues=self.snapshot()
        key=sha(canon([query,limit,depth,self.scope,bool(self.embedder),'rrf-v3-lexical-ranked-context-reserved']).encode())
        with self.connect() as c:cached=c.execute('SELECT generation,result FROM cache WHERE key=?',(key,)).fetchone()
        if cached and cached[0]==generation:
            result=json.loads(cached[1]);result['cache_reused']=True
            self.log(query,generation,result,True);return result
        eligible={i:r for i,r in records.items() if i not in invalid and r.get('lifecycle_status')!='excluded'}
        # Expansões do grafo não são posições no ranking lexical do RRF.
        lexical=self.k.search(query,limit=limit,depth=0)
        exact=list(dict.fromkeys(r['id'] for r in lexical['results'] if r['id'] in eligible))
        semantic=[]
        if self.embedder and eligible:
            with self.connect() as c:existing={r[0]:r[1] for r in c.execute('SELECT DISTINCT id,digest FROM vectors')}
            updates={}
            for ident,record in eligible.items():
                text=record['title']+'\n'+canon(record['payload']);digest=sha(text.encode())
                if existing.get(ident)!=digest:updates[ident]=(digest,self.embedder.chunks(text))
            if self.snapshot()[0]!=generation:raise Conflict('base mudou durante atualização do índice')
            with self.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                for ident in set(existing)-set(eligible):c.execute('DELETE FROM vectors WHERE id=?',(ident,))
                for ident,(digest,vectors) in updates.items():
                    c.execute('DELETE FROM vectors WHERE id=?',(ident,))
                    for part,vector in enumerate(vectors):c.execute('INSERT INTO vectors VALUES(?,?,?,?)',(ident,part,digest,canon(vector)))
                c.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('generation',generation))
                vectors=list(c.execute('SELECT id,value FROM vectors'))
            queries=self.embedder.chunks(query,'query');scores={}
            for ident,raw in vectors:
                if ident not in eligible:continue
                vector=json.loads(raw)
                score=max(sum(a*b for a,b in zip(vector,q)) for q in queries)
                scores[ident]=max(scores.get(ident,float('-inf')),score)
            semantic=sorted(scores,key=lambda i:(-scores[i],i))[:limit]
        ranks={}
        for channel in (exact,semantic):
            for position,ident in enumerate(channel):ranks[ident]=ranks.get(ident,0)+1/(60+position+1)
        lexical_positions={ident:position for position,ident in enumerate(exact)}
        semantic_positions={ident:position for position,ident in enumerate(semantic)}
        ranked=sorted(ranks,key=lambda i:(-ranks[i],lexical_positions.get(i,limit),
                                         semantic_positions.get(i,limit),i))
        reserve=min(3,max(1,limit//3)) if depth and limit>1 else 0
        selected=ranked[:max(1,limit-reserve)]
        visited=set(selected)
        for _ in range(depth):
            extra=[];frontier=set(selected)
            for ident in selected:
                for ref in refs(records[ident]['payload']):
                    target=ref.get('record_id')
                    if target in eligible and target not in visited:visited.add(target);extra.append(target)
            for ident in sorted(eligible):
                if ident not in visited and any(ref.get('record_id') in frontier for ref in refs(records[ident]['payload'])):
                    visited.add(ident);extra.append(ident)
            selected=(selected+extra)[:limit]
        selected=(selected+[ident for ident in ranked if ident not in selected])[:limit]
        if self.snapshot()[0]!=generation:raise Conflict('base mudou antes de concluir recuperação')
        result={'mode':'hybrid_lexical_vector_graph' if self.embedder else 'lexical_and_graph',
                'generation':generation,'cache_reused':False,'scope':self.scope,
                'results':[{'id':ident,'revision':records[ident]['revision'],'title':records[ident]['title'],
                            'record_type':records[ident]['record_type'],'record':records[ident]} for ident in selected],
                'issues':issues,'excluded_stale':len(invalid),
                'limits':['Ranking não comprova identidade, veracidade ou causalidade.','A resposta usa a nota canônica completa, não somente o vetor.']}
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)',(key,generation,canon(result)))
            recipe=sha(canon([query,self.scope]).encode())
            c.execute('INSERT INTO recipes VALUES(?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET uses=uses+1,last_generation=excluded.last_generation',
                      (recipe,query,canon(['lexical','vector' if self.embedder else 'vector_unavailable','graph']),1,generation))
        self.log(query,generation,result,False);return result
    def log(self,query,generation,result,reused):
        with self.connect() as c:c.execute('INSERT INTO history(at,query,generation,reused,result_ids) VALUES(?,?,?,?,?)',
                   (NOW(),query,generation,int(reused),canon([r['id'] for r in result['results']])))
