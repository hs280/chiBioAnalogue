import olefile, sys, re, collections, json
def load(path):
    o=olefile.OleFileIO(path)
    raw=o.openstream("FileHeader").read()
    recs=[]; i=0
    while i+4<=len(raw):
        n=int.from_bytes(raw[i:i+3],'little'); fl=raw[i+3]; i+=4
        blob=raw[i:i+n]; i+=n
        if fl!=0: continue
        t=blob.rstrip(b'\x00').decode('latin-1')
        d={}
        for kv in t.split('|'):
            if '=' in kv:
                k,v=kv.split('=',1); d[k.upper()]=v
        recs.append(d)
    return recs
if __name__=="__main__":
    recs=load(sys.argv[1])
    print(len(recs),"records")
    c=collections.Counter(r.get('RECORD') for r in recs); print(sorted(c.items(), key=lambda x:int(x[0]) if x[0] else -1))
