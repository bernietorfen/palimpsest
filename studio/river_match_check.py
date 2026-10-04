"""Check matched rendered reference views and changed wider views on RunPod."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image


def main(args):
    folder=Path(args.proof);destination=Path(args.output)
    destination.mkdir(parents=True,exist_ok=False)
    proof=json.loads((folder/'proof.json').read_text())
    def frame(view,time):
        item=next(p for p in proof['frames'] if p['view']==view and p['film_time']==time)
        path=folder/item['image']
        return item,np.array(Image.open(path).convert('RGB'),dtype=np.int16),path
    records={}
    for view in ('local','wide'):
        reference,base,path=frame(view,0.)
        comparisons=[]
        for seconds in (104.,208.):
            item,pixels,returned_path=frame(view,seconds)
            difference=np.abs(base-pixels)
            for key in ('camera_location','camera_lens','camera_rotation'):
                assert item[key]==reference[key],(view,seconds,key)
            maximum=int(difference.max());mean=float(difference.mean())
            if view=='local':assert maximum<=2
            else:assert mean>1.
            comparisons.append({'film_time':seconds,'maximum_rgb_difference':maximum,
                                'mean_absolute_rgb_difference':mean,
                                'fraction_identical_pixels':float(np.mean(np.all(difference==0,axis=2))),
                                'image_sha256':hashlib.sha256(returned_path.read_bytes()).hexdigest()})
        records[view]={'reference_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                       'comparisons':comparisons}
    _,black,_=frame('local',120.)
    assert int(black.max())<=1
    records['blackout_maximum_rgb']=int(black.max())
    records['proof_sha256']=hashlib.sha256((folder/'proof.json').read_bytes()).hexdigest()
    records['scope']='Exact pixel comparisons concern these controlled renders only. They do not assert similarity of other nonlinear images or a perceptual response.'
    shutil.copyfile(__file__,destination/'river_match_check.py')
    (destination/'comparison.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof',required=True)
    parser.add_argument('--output',required=True)
    main(parser.parse_args())
