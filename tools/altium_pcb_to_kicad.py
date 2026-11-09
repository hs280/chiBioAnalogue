import sys, pcbnew
src, dst = sys.argv[1], sys.argv[2]
b = pcbnew.IO_MGR.Load(pcbnew.IO_MGR.ALTIUM_DESIGNER, src)
print("footprints:", len(b.GetFootprints()), "tracks:", len(b.GetTracks()), "nets:", b.GetNetCount(), "zones:", len(b.Zones()))
bb = b.GetBoardEdgesBoundingBox()
print("outline mm: %.2f x %.2f" % (pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())))
b.Save(dst)
fps = sorted(b.GetFootprints(), key=lambda f: f.GetReference())
for f in fps[:200]:
    p = f.GetPosition()
    print(f.GetReference(), f.GetValue(), f.GetFPIDAsString() or '-', "(%.2f,%.2f)" % (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)), "B" if f.IsFlipped() else "T", "pads=%d" % len(f.Pads()))
