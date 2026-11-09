import sys, importlib.util, collections, json
# Usage: python3 altium_sch_netlist.py altium_sch_parse.py Side.SchDoc far netlist.json
spec=importlib.util.spec_from_file_location("p",sys.argv[1]); p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
recs=p.load(sys.argv[2]); mode=sys.argv[3]  # pin end mode: 'far' or 'near'
body=recs[1:]  # OWNERINDEX is relative to records after header
def xy(r,k):
    return float(r.get(k+'.X',0))+float(r.get(k+'.X_FRAC',0))/1e5, float(r.get(k+'.Y',0))+float(r.get(k+'.Y_FRAC',0))/1e5
# designators
ref={}
for r in body:
    if r.get('RECORD')=='34' and r.get('NAME')=='Designator': ref[int(r['OWNERINDEX'])]=r['TEXT']
comp={i:r for i,r in enumerate(body) if r.get('RECORD')=='1'}
print("components with designator:", sum(1 for i in comp if i in ref), "of", len(comp), file=sys.stderr)
parent={}
def find(a):
    parent.setdefault(a,a)
    while parent[a]!=a:
        parent[a]=parent[parent[a]]; a=parent[a]
    return a
def union(a,b): parent[find(a)]=find(b)
def pt(x,y): return (round(x,1),round(y,1))
wires=[]
for r in body:
    if r.get('RECORD')=='27':
        n=int(r['LOCATIONCOUNT']); pts=[pt(float(r['X%d'%k])+float(r.get('X%d_FRAC'%k,0))/1e5, float(r['Y%d'%k])+float(r.get('Y%d_FRAC'%k,0))/1e5) for k in range(1,n+1)]
        for a,b in zip(pts,pts[1:]): wires.append((a,b)); union(('P',a),('P',b))
def on_seg(q,a,b,t=0.15):
    (x,y),(x1,y1),(x2,y2)=q,a,b
    if abs(x1-x2)<1e-6 and abs(x-x1)<t and min(y1,y2)-t<=y<=max(y1,y2)+t: return True
    if abs(y1-y2)<1e-6 and abs(y-y1)<t and min(x1,x2)-t<=x<=max(x1,x2)+t: return True
    return False
def attach(q):
    q=pt(*q); hit=False
    for a,b in wires:
        if on_seg(q,a,b): union(('P',q),('P',a)); hit=True
    return hit
dx={0:(1,0),1:(0,1),2:(-1,0),3:(0,-1)}
pins=[]; floating=[]
for i,r in enumerate(body):
    if r.get('RECORD')=='2':
        o=int(r.get('OWNERINDEX',-1)); x,y=xy(r,'LOCATION'); L=float(r.get('PINLENGTH',0)); ori=int(r.get('PINCONGLOMERATE',0))&3
        ex,ey=(x+dx[ori][0]*L,y+dx[ori][1]*L) if mode=='far' else (x,y)
        q=pt(ex,ey); hit=attach(q)
        pins.append((ref.get(o,'?%d'%o),r.get('DESIGNATOR'),r.get('NAME'),q)); 
        parent.setdefault(('P',q),('P',q)); 
        if not hit: floating.append(pins[-1])
# junctions
for r in body:
    if r.get('RECORD')=='29': attach(xy(r,'LOCATION'))
names=collections.defaultdict(list)
for r in body:
    if r.get('RECORD') in ('25','17','18'):
        q=pt(*xy(r,'LOCATION')); attach(q); parent.setdefault(('P',q),('P',q))
        names[r['TEXT']].append(q)
for t,qs in names.items():
    for q in qs[1:]: union(('P',qs[0]),('P',q))
nets=collections.defaultdict(lambda:{'names':set(),'pins':[]})
for t,qs in names.items(): nets[find(('P',qs[0]))]['names'].add(t)
for rf,pn,nm,q in pins: nets[find(('P',q))]['pins'].append((rf,pn,nm))
out=[]
for k,v in nets.items():
    out.append({'names':sorted(v['names']),'pins':sorted(v['pins'])})
json.dump({'nets':out,'floating':floating,'refs':sorted(set(ref.values()))},open(sys.argv[4],'w'),indent=1)
print(mode,"nets:",len(out),"pins:",len(pins),"floating pins:",len(floating),file=sys.stderr)
