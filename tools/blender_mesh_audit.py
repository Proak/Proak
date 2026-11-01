"""Blender CLI usage: blender -b source.blend --python tools/blender_mesh_audit.py
Works only with real bpy. Requires actual .blend open. Writes a JSON report next to blend.
"""
import bpy,bmesh,json,math
from pathlib import Path
scene=bpy.context.scene
objects=[o for o in scene.objects if o.type=='MESH']
items=[];fail=[]
for ob in objects:
 mesh=ob.data;bm=bmesh.new();bm.from_mesh(mesh)
 nonmanifold=sum(1 for e in bm.edges if not e.is_manifold)
 degenerate=sum(1 for p in bm.faces if p.calc_area()<1e-8)
 tris=sum(max(len(p.verts)-2,0) for p in bm.faces)
 missing_uv=(len(mesh.uv_layers)==0)
 unapplied=any(abs(s-1.0)>1e-4 for s in ob.scale)
 item={'name':ob.name,'triangles':tris,'non_manifold_edges':nonmanifold,'degenerate_faces':degenerate,'has_uv':not missing_uv,'unapplied_scale':unapplied,'dimensions_m':list(ob.dimensions)}
 items.append(item)
 if nonmanifold: fail.append(ob.name+':non-manifold')
 if degenerate: fail.append(ob.name+':degenerate')
 if missing_uv: fail.append(ob.name+':no UV')
 if unapplied: fail.append(ob.name+':scale not applied')
 bm.free()
output={'kind':'BLENDER_REAL_RUN','passed':not fail,'scene':bpy.data.filepath,'mesh_objects':len(objects),'meshes':items,'issues':fail,'note':'This checks geometry only; does not prove excellent artistic quality or UE collision/performance.'}
p=Path(bpy.data.filepath).with_suffix('.mesh_audit.json')
p.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':output['passed'],'report':str(p)},ensure_ascii=False))
if fail: raise SystemExit(1)
