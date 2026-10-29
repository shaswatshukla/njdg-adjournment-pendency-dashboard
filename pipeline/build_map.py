"""Convert a manually downloaded LGD boundary layer to a small offline SVG-path asset.

Usage: python pipeline/build_map.py path/to/LGD_States.geojson
No downloads, map API, case data or extra dependencies are used by this script.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {'JAMMU & KASHMIR':'Jammu and Kashmir', 'ANDAMAN & NICOBAR':'Andaman and Nicobar Islands',
           'DADRA,NAGAR HAVELI,DAMAN & DIU':'Dadra and Nagar Haveli and Daman and Diu'}
ABBR = dict(zip(['Andaman and Nicobar Islands','Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chandigarh','Chhattisgarh','Dadra and Nagar Haveli and Daman and Diu','Delhi','Goa','Gujarat','Haryana','Himachal Pradesh','Jammu and Kashmir','Jharkhand','Karnataka','Kerala','Ladakh','Lakshadweep','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Puducherry','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal'],
                ['AN','AP','AR','AS','BR','CH','CG','DN','DL','GA','GJ','HR','HP','JK','JH','KA','KL','LA','LD','MP','MH','MN','ML','MZ','NL','OD','PY','PB','RJ','SK','TN','TS','TR','UP','UK','WB']))
MARKERS = {'Chandigarh':(76.78,30.73),'Delhi':(77.2,28.6),'Puducherry':(79.8,11.9),
           'Dadra and Nagar Haveli and Daman and Diu':(72.9,20.3),'Lakshadweep':(72.8,10.5),
           'Andaman and Nicobar Islands':(92.8,11.7)}


def simplify(points, tolerance=.45):
    """Iterative Ramer–Douglas–Peucker, in SVG pixels; tiny rings retain their shape."""
    if len(points)<5:return points
    keep={0,len(points)-1};stack=[(0,len(points)-1)]
    while stack:
        a,b=stack.pop();x,y=points[a];dx=points[b][0]-x;dy=points[b][1]-y;den=dx*dx+dy*dy
        distance,index=0,None
        for i in range(a+1,b):
            px,py=points[i];t=max(0,min(1,((px-x)*dx+(py-y)*dy)/den)) if den else 0
            d=(px-x-t*dx)**2+(py-y-t*dy)**2
            if d>distance:distance,index=d,i
        if distance>tolerance*tolerance:
            keep.add(index);stack.extend([(a,index),(index,b)])
    result=[points[i] for i in sorted(keep)]
    return result if len(result)>=4 or points[0]!=points[-1] else points


def build_map(path):
    raw=Path(path).read_bytes();geo=json.loads(raw)
    expected=set(ABBR);shapes={};all_points=[]
    for feature in geo['features']:
        label=feature['properties']['STNAME'];state=ALIASES.get(label,label.title())
        if state not in expected or state in shapes:raise ValueError('Unknown or duplicate boundary identity: '+state)
        g=feature['geometry'];polygons=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'] if g['type']=='MultiPolygon' else None
        if not polygons:raise ValueError('Boundary geometry must be polygonal')
        shapes[state]=(polygons,feature['properties']['State_LGD'])
        for polygon in polygons:
            for ring in polygon:
                for lon,lat,*_ in ring:
                    if not math.isfinite(lon+lat) or not 60<lon<105 or not 0<lat<45:raise ValueError('Boundary coordinate outside expected geographic range')
                    all_points.append((lon*math.cos(math.radians(22)),lat))
    if set(shapes)!=expected:raise ValueError('Exactly all 36 State/UT boundaries are required')
    xmin=min(x for x,y in all_points);xmax=max(x for x,y in all_points)
    ymin=min(y for x,y in all_points);ymax=max(y for x,y in all_points)
    scale=min(740/(xmax-xmin),820/(ymax-ymin));ox=(800-scale*(xmax-xmin))/2;oy=(880-scale*(ymax-ymin))/2
    def project(p):return [round(ox+(p[0]*math.cos(math.radians(22))-xmin)*scale,2),round(oy+(ymax-p[1])*scale,2)]
    features=[]
    for state,(polygons,code) in shapes.items():
        commands=[];boxes=[]
        for polygon in polygons:
            for index,ring in enumerate(polygon):
                pts=simplify([project(p) for p in ring]);commands.append('M'+'L'.join(f'{x},{y}' for x,y in pts)+'Z')
                if index==0:
                    xs=[p[0] for p in pts];ys=[p[1] for p in pts];boxes.append([min(xs),min(ys),max(xs),max(ys)])
        box=max(boxes,key=lambda b:(b[2]-b[0])*(b[3]-b[1]))
        label=project(MARKERS[state]) if state in MARKERS else [round((box[0]+box[2])/2,2),round((box[1]+box[3])/2,2)]
        features.append({'state':state,'lgd_code':int(code),'abbr':ABBR[state],'path':''.join(commands),
                         'label':label,'marker':state in MARKERS})
    result={'viewBox':[0,0,800,880],'features':sorted(features,key=lambda f:f['state']),
            'source':{'title':'LGD States (2024), distributed by Bharatlas','publisher':'Bharatlas / Local Government Directory',
                      'url':'https://bharatlas.com/api/dl/admin/states/LGD_States.geojson','catalogue_url':'https://bharatlas.com/',
                      'download_date':'2026-10-29','source_sha256':hashlib.sha256(raw).hexdigest(),
                      'licence':'CC0-1.0 / CC-BY-4.0, as stated by the publisher; attribution retained',
                      'attribution':'State/UT geometry: Local Government Directory, via Bharatlas. Simplified for this dashboard.',
                      'method':'Equirectangular display at 22 degrees north; RDP tolerance 0.45 SVG pixels; no area/rate calculations use this geometry.',
                      'limitations':'Reference boundaries, not a survey record. Small UT dots are enlarged click targets, not areas. Boundary vintage 2024; crime observations are 2023.'}}
    output=ROOT/'site/assets/maps/india-states.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
    return output


if __name__=='__main__':
    print(build_map(sys.argv[1]))
